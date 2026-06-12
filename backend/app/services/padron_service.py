from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.core.config import get_settings
from app.core.security import decrypt_value, encrypt_value
from app.integrations.moodle_ws import MoodleWSClient, MoodleWSError
from app.models.base import Tenant
from app.models.padron import EntradaPadron, VersionPadron
from app.repositories.padron import EntradaPadronRepository, VersionPadronRepository
from app.repositories.usuarios import UsuarioRepository
from app.schemas.padron import (
    CargarPadronResponse,
    DescartePadronResponse,
    EntradaPadronItem,
    PadronActivoResponse,
)
from app.services.padron_parser import ParseError, parse_file


class NotFoundError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PadronService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._version_repo = VersionPadronRepository(session=session, tenant_id=self.tenant_id)
        self._entrada_repo = EntradaPadronRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)

    def _hash_email(self, email: str) -> str:
        secret = get_settings().secret_key.encode("utf-8")
        return hmac.new(secret, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()

    def _build_entrada(self, version_id: uuid.UUID, row: dict) -> EntradaPadron:
        email = row.get("email", "").strip()
        return EntradaPadron(
            tenant_id=self.tenant_id,
            version_id=version_id,
            nombre=row.get("nombre", "").strip(),
            apellidos=row.get("apellidos", "").strip(),
            email_encrypted=encrypt_value(email) if email else "",
            email_hash=self._hash_email(email) if email else "",
            comision=row.get("comision") or None,
            regional=row.get("regional") or None,
        )

    async def cargar_desde_archivo(
        self,
        *,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        content: bytes,
        filename: str,
        ip: str | None = None,
    ) -> CargarPadronResponse:
        rows = parse_file(content, filename)
        return await self._cargar_rows(
            actor_id=actor_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            rows=rows,
            ip=ip,
        )

    async def cargar_desde_moodle(
        self,
        *,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        moodle_course_id: int,
        ip: str | None = None,
    ) -> CargarPadronResponse:
        tenant = await self.session.scalar(select(Tenant).where(Tenant.id == self.tenant_id))
        if not tenant or not tenant.moodle_ws_url or not tenant.moodle_ws_token_encrypted:
            raise NotFoundError("Este tenant no tiene Moodle Web Services configurado")

        token = decrypt_value(tenant.moodle_ws_token_encrypted)
        client = MoodleWSClient(base_url=tenant.moodle_ws_url, token=token)
        users = await client.get_enrolled_users(moodle_course_id)

        rows = [
            {
                "nombre": u.get("firstname", ""),
                "apellidos": u.get("lastname", ""),
                "email": u.get("email", ""),
                "comision": None,
                "regional": None,
            }
            for u in users
        ]

        return await self._cargar_rows(
            actor_id=actor_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            rows=rows,
            ip=ip,
        )

    async def _cargar_rows(
        self,
        *,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        rows: list[dict],
        ip: str | None,
    ) -> CargarPadronResponse:
        # actor_id is auth_user_id from JWT; cargado_por FK references usuario.id
        usuario = await self._usuario_repo.get_by_auth_user_id(actor_id)
        cargado_por = usuario.id if usuario else actor_id

        version_anterior_desactivada = await self._version_repo.desactivar_anterior(materia_id, cohorte_id)
        version = await self._version_repo.create_version(materia_id, cohorte_id, cargado_por=cargado_por)

        entradas = [self._build_entrada(version.id, row) for row in rows]
        await self._entrada_repo.bulk_create(entradas)

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="PADRON_CARGAR",
            detalle={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id), "entradas": len(entradas)},
            filas_afectadas=len(entradas),
            ip=ip,
        )

        return CargarPadronResponse(
            version_id=version.id,
            entradas_cargadas=len(entradas),
            version_anterior_desactivada=version_anterior_desactivada,
        )

    async def get_padron_activo(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> PadronActivoResponse:
        version = await self._version_repo.get_activa(materia_id, cohorte_id)
        if version is None:
            return PadronActivoResponse(version_id=None, cargado_at=None, entradas=[])

        entradas = await self._entrada_repo.list_by_version(version.id)
        items = [
            EntradaPadronItem(
                id=e.id,
                usuario_id=e.usuario_id,
                nombre=e.nombre,
                apellidos=e.apellidos,
                email=decrypt_value(e.email_encrypted) if e.email_encrypted else "",
                comision=e.comision,
                regional=e.regional,
            )
            for e in entradas
        ]

        return PadronActivoResponse(
            version_id=version.id,
            cargado_at=version.cargado_at,
            entradas=items,
        )

    async def descartar_padron(
        self,
        *,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        ip: str | None = None,
    ) -> DescartePadronResponse:
        version = await self._version_repo.get_activa(materia_id, cohorte_id)
        if version is None:
            raise NotFoundError("No hay padrón activo para esta materia/cohorte")

        entradas = await self._entrada_repo.list_by_version(version.id)
        count = len(entradas)

        await self._version_repo.desactivar_anterior(materia_id, cohorte_id)

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="PADRON_CARGAR",
            detalle={"operacion": "descarte", "materia_id": str(materia_id), "cohorte_id": str(cohorte_id)},
            filas_afectadas=count,
            ip=ip,
        )

        return DescartePadronResponse(entradas_descartadas=count)
