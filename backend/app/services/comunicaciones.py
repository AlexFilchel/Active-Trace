from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.core.config import get_settings
from app.core.dependencies import AuthenticatedUser
from app.core.security import decrypt_value, encrypt_value
from app.models.comunicacion import Comunicacion
from app.repositories.comunicaciones import CommunicationApprovalPolicy, CommunicationRecipientRepository, CommunicationTenantRepository, ComunicacionRepository, utc_now


logger = logging.getLogger(__name__)
_ALLOWED_STATES = {
    "Pendiente": {"Enviando", "Cancelado"},
    "Enviando": {"Enviado", "Error"},
    "Enviado": set(),
    "Error": set(),
    "Cancelado": set(),
}


class CommunicationError(Exception):
    status_code = 400

    def __init__(self, detail: str, *, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class PreviewRecipient:
    entry_id: uuid.UUID
    email: str
    nombre: str
    apellidos: str


class CommunicationProvider:
    async def send(self, *, recipient: str, subject: str, body: str, idempotency_key: str) -> str:
        raise NotImplementedError


class FakeCommunicationProvider(CommunicationProvider):
    async def send(self, *, recipient: str, subject: str, body: str, idempotency_key: str) -> str:
        return f"fake:{idempotency_key}"


class FailingCommunicationProvider(CommunicationProvider):
    async def send(self, *, recipient: str, subject: str, body: str, idempotency_key: str) -> str:
        raise RuntimeError("provider-failure")


class ComunicacionService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = ComunicacionRepository(session=session, tenant_id=self.tenant_id)
        self._recipient_repo = CommunicationRecipientRepository(session=session, tenant_id=self.tenant_id)
        self._tenant_repo = CommunicationTenantRepository(session=session)

    def _mask_email(self, email: str) -> str:
        local, _, domain = email.partition("@")
        masked_local = f"{local[:1]}***" if local else "***"
        return f"{masked_local}@{domain}" if domain else masked_local

    def _render_template(self, template: str, *, nombre: str, apellidos: str, materia: str) -> str:
        rendered = template
        for key, value in {
            "{{nombre}}": nombre,
            "{{apellidos}}": apellidos,
            "{{materia}}": materia,
        }.items():
            rendered = rendered.replace(key, value)
        return rendered

    async def _resolve_preview_context(self, *, materia_id: uuid.UUID, destinatarios: list[uuid.UUID]) -> tuple[str, list[PreviewRecipient]]:
        materia = await self._recipient_repo.get_materia(materia_id)
        if materia is None:
            raise CommunicationError("Materia no encontrada.", status_code=404)

        entries = await self._recipient_repo.list_entries(destinatarios)
        entry_by_id = {entry.id: entry for entry in entries}
        recipients: list[PreviewRecipient] = []
        for entry_id in destinatarios:
            entry = entry_by_id.get(entry_id)
            if entry is None:
                raise CommunicationError("Destinatario no encontrado.", status_code=404)
            recipients.append(
                PreviewRecipient(
                    entry_id=entry.id,
                    email=decrypt_value(entry.email_encrypted),
                    nombre=entry.nombre,
                    apellidos=entry.apellidos,
                )
            )
        return materia.nombre, recipients

    def _build_preview_token(
        self,
        *,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        destinatarios: list[uuid.UUID],
        asunto_template: str,
        cuerpo_template: str,
        expires_at: datetime,
    ) -> str:
        payload = {
            "actor_id": str(actor_id),
            "tenant_id": str(self.tenant_id),
            "materia_id": str(materia_id),
            "destinatarios": [str(destinatario) for destinatario in destinatarios],
            "asunto_template": asunto_template,
            "cuerpo_template": cuerpo_template,
            "expires_at": expires_at.isoformat(),
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = hmac.new(get_settings().secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
        return f"{encoded}.{signature}"

    def _validate_preview_token(
        self,
        *,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        destinatarios: list[uuid.UUID],
        asunto_template: str,
        cuerpo_template: str,
        preview_token: str,
    ) -> None:
        try:
            encoded, signature = preview_token.split(".", maxsplit=1)
            raw = base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
            expected = hmac.new(get_settings().secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise CommunicationError("Preview inválido.", status_code=422)
            payload = json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            raise CommunicationError("Preview inválido.", status_code=422)

        if payload["actor_id"] != str(actor_id) or payload["tenant_id"] != str(self.tenant_id):
            raise CommunicationError("Preview inválido.", status_code=422)
        if payload["materia_id"] != str(materia_id):
            raise CommunicationError("Preview inválido.", status_code=422)
        if payload["destinatarios"] != [str(destinatario) for destinatario in destinatarios]:
            raise CommunicationError("Preview inválido.", status_code=422)
        if payload["asunto_template"] != asunto_template or payload["cuerpo_template"] != cuerpo_template:
            raise CommunicationError("Preview inválido.", status_code=422)
        if datetime.fromisoformat(payload["expires_at"]) < datetime.now(timezone.utc):
            raise CommunicationError("Preview expirado.", status_code=422)

    def _transition(self, comunicacion: Comunicacion, target_state: str) -> None:
        if target_state not in _ALLOWED_STATES.get(comunicacion.estado, set()):
            raise CommunicationError("Transición inválida.", status_code=409)
        comunicacion.estado = target_state

    def _resolve_requires_approval(self, policy: CommunicationApprovalPolicy, *, recipient_count: int) -> bool:
        if recipient_count > 1:
            if policy.requires_massive_approval is not None:
                return policy.requires_massive_approval
            if policy.requires_approval is not None:
                return policy.requires_approval
            return True
        if policy.requires_approval is not None:
            return policy.requires_approval
        return False

    async def _requires_approval(self, recipient_count: int) -> bool:
        policy = await self._tenant_repo.get_approval_policy(self.tenant_id)
        return self._resolve_requires_approval(policy, recipient_count=recipient_count)

    def _serialize(self, comunicacion: Comunicacion) -> dict[str, object]:
        email = decrypt_value(comunicacion.destinatario_encrypted)
        return {
            "id": comunicacion.id,
            "lote_id": comunicacion.lote_id,
            "materia_id": comunicacion.materia_id,
            "entrada_padron_id": comunicacion.entrada_padron_id,
            "estado": comunicacion.estado,
            "requiere_aprobacion": comunicacion.requiere_aprobacion,
            "intentos": comunicacion.intentos,
            "destinatario_masked": self._mask_email(email),
            "asunto": comunicacion.asunto,
            "created_at": comunicacion.created_at,
            "aprobado_at": comunicacion.aprobado_at,
            "enviado_at": comunicacion.enviado_at,
            "cancelado_at": comunicacion.cancelado_at,
        }

    async def preview(self, *, user: AuthenticatedUser, materia_id: uuid.UUID, destinatarios: list[uuid.UUID], asunto_template: str, cuerpo_template: str) -> dict[str, object]:
        materia_nombre, recipients = await self._resolve_preview_context(materia_id=materia_id, destinatarios=destinatarios)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        return {
            "preview_token": self._build_preview_token(
                actor_id=user.user_id,
                materia_id=materia_id,
                destinatarios=destinatarios,
                asunto_template=asunto_template,
                cuerpo_template=cuerpo_template,
                expires_at=expires_at,
            ),
            "expires_at": expires_at,
            "items": [
                {
                    "entrada_padron_id": recipient.entry_id,
                    "asunto": self._render_template(asunto_template, nombre=recipient.nombre, apellidos=recipient.apellidos, materia=materia_nombre),
                    "cuerpo": self._render_template(cuerpo_template, nombre=recipient.nombre, apellidos=recipient.apellidos, materia=materia_nombre),
                    "destinatario_masked": self._mask_email(recipient.email),
                }
                for recipient in recipients
            ],
        }

    async def enqueue(
        self,
        *,
        user: AuthenticatedUser,
        materia_id: uuid.UUID,
        destinatarios: list[uuid.UUID],
        asunto_template: str,
        cuerpo_template: str,
        idempotency_key: str,
        preview_token: str,
    ) -> dict[str, object]:
        self._validate_preview_token(
            actor_id=user.user_id,
            materia_id=materia_id,
            destinatarios=destinatarios,
            asunto_template=asunto_template,
            cuerpo_template=cuerpo_template,
            preview_token=preview_token,
        )

        existing = await self._repo.list_by_idempotency_key(idempotency_key)
        if existing:
            return {"lote_id": existing[0].lote_id, "reused": True, "comunicaciones": [self._serialize(item) for item in existing]}

        materia_nombre, recipients = await self._resolve_preview_context(materia_id=materia_id, destinatarios=destinatarios)
        lote_id = uuid.uuid4()
        requires_approval = await self._requires_approval(len(recipients))
        rows: list[Comunicacion] = []
        for recipient in recipients:
            rows.append(
                await self._repo.create(
                    materia_id=materia_id,
                    entrada_padron_id=recipient.entry_id,
                    enviado_por=user.user_id,
                    destinatario_encrypted=encrypt_value(recipient.email),
                    asunto=self._render_template(asunto_template, nombre=recipient.nombre, apellidos=recipient.apellidos, materia=materia_nombre),
                    cuerpo=self._render_template(cuerpo_template, nombre=recipient.nombre, apellidos=recipient.apellidos, materia=materia_nombre),
                    estado="Pendiente",
                    lote_id=lote_id,
                    idempotency_key=idempotency_key,
                    requiere_aprobacion=requires_approval,
                )
            )

        await audit_action(
            session=self.session,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            accion="COMUNICACION_ENVIAR",
            filas_afectadas=len(rows),
            materia_id=materia_id,
            detalle={"lote_id": str(lote_id), "filas_afectadas": len(rows)},
            impersonando_id=user.impersonating_user_id,
        )
        return {"lote_id": lote_id, "reused": False, "comunicaciones": [self._serialize(item) for item in rows]}

    async def approve_lote(self, *, user: AuthenticatedUser, lote_id: uuid.UUID) -> int:
        rows = await self._repo.list_by_lote_id(lote_id)
        approved = 0
        now = utc_now()
        for row in rows:
            if row.estado == "Pendiente" and row.aprobado_at is None:
                row.aprobado_at = now
                row.aprobado_por = user.user_id
                approved += 1
        await self.session.flush()
        await audit_action(
            session=self.session,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            accion="COMUNICACION_APROBAR",
            filas_afectadas=approved,
            detalle={"lote_id": str(lote_id), "filas_afectadas": approved},
            impersonando_id=user.impersonating_user_id,
        )
        return approved

    async def approve_one(self, *, user: AuthenticatedUser, comunicacion_id: uuid.UUID) -> int:
        row = await self._repo.get(comunicacion_id)
        if row is None:
            raise CommunicationError("Comunicación no encontrada.", status_code=404)
        if row.estado != "Pendiente":
            raise CommunicationError("Solo se aprueban pendientes.", status_code=409)
        if row.aprobado_at is None:
            row.aprobado_at = utc_now()
            row.aprobado_por = user.user_id
            await self.session.flush()
            await audit_action(
                session=self.session,
                actor_id=user.user_id,
                tenant_id=user.tenant_id,
                accion="COMUNICACION_APROBAR",
                filas_afectadas=1,
                detalle={"comunicacion_id": str(row.id), "lote_id": str(row.lote_id), "filas_afectadas": 1},
                materia_id=row.materia_id,
                impersonando_id=user.impersonating_user_id,
            )
            return 1
        return 0

    async def cancel(self, *, user: AuthenticatedUser, comunicacion_id: uuid.UUID) -> Comunicacion:
        row = await self._repo.get(comunicacion_id)
        if row is None:
            raise CommunicationError("Comunicación no encontrada.", status_code=404)
        self._transition(row, "Cancelado")
        row.cancelado_at = utc_now()
        row.cancelado_por = user.user_id
        await self.session.flush()
        await audit_action(
            session=self.session,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            accion="COMUNICACION_CANCELAR",
            filas_afectadas=1,
            materia_id=row.materia_id,
            detalle={"comunicacion_id": str(row.id), "lote_id": str(row.lote_id), "filas_afectadas": 1},
            impersonando_id=user.impersonating_user_id,
        )
        return row

    async def list_items(self) -> list[dict[str, object]]:
        rows = await self._repo.list()
        return [self._serialize(row) for row in rows]


class CommunicationDispatchService:
    def __init__(self, *, session: AsyncSession, provider: CommunicationProvider, max_retries: int = 2) -> None:
        self.session = session
        self.provider = provider
        self.max_retries = max_retries
        self._tenant_repo = CommunicationTenantRepository(session=session)

    def _transition(self, comunicacion: Comunicacion, target_state: str) -> None:
        if target_state not in _ALLOWED_STATES.get(comunicacion.estado, set()):
            raise CommunicationError("Transición inválida.", status_code=409)
        comunicacion.estado = target_state

    async def _deliver(self, comunicacion: Comunicacion) -> None:
        recipient = decrypt_value(comunicacion.destinatario_encrypted)
        self._transition(comunicacion, "Enviando")
        await self.session.flush()
        last_error: Exception | None = None
        for _ in range(max(1, self.max_retries)):
            try:
                provider_message_id = await self.provider.send(
                    recipient=recipient,
                    subject=comunicacion.asunto,
                    body=comunicacion.cuerpo,
                    idempotency_key=str(comunicacion.id),
                )
                self._transition(comunicacion, "Enviado")
                comunicacion.enviado_at = utc_now()
                comunicacion.provider_message_id = provider_message_id
                comunicacion.error_detalle = None
                return
            except Exception as exc:
                last_error = exc
                comunicacion.intentos += 1
                comunicacion.error_detalle = exc.__class__.__name__
        self._transition(comunicacion, "Error")
        logger.info(
            "communication-dispatch-failed",
            extra={
                "comunicacion_id": str(comunicacion.id),
                "tenant_id": str(comunicacion.tenant_id),
                "estado": comunicacion.estado,
                "error_type": last_error.__class__.__name__ if last_error is not None else "UnknownError",
            },
        )

    async def process_pending(self, *, limit: int = 50) -> int:
        processed = 0
        for tenant_id in await self._tenant_repo.list_tenant_ids_with_pending():
            repo = ComunicacionRepository(session=self.session, tenant_id=tenant_id)
            for comunicacion in await repo.list_dispatchable_for_update(limit=limit):
                if comunicacion.estado == "Cancelado":
                    continue
                await self._deliver(comunicacion)
                processed += 1
            await self.session.flush()
        return processed
