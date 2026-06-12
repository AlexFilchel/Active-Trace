from __future__ import annotations

import hashlib
import hmac
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.core.config import get_settings
from app.models.padron import EntradaPadron, VersionPadron
from app.repositories.calificacion import CalificacionRepository
from app.repositories.umbral import UmbralRepository
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository
from app.schemas.calificaciones import (
    ImportarResponse,
    PreviewResponse,
    ReporteFinalizacionResponse,
    SinCalificarItem,
    UmbralRequest,
    UmbralResponse,
    VaciadoResponse,
)
from app.services.lms_parser import detectar_actividades, extraer_calificaciones

_DEFAULT_UMBRAL_PCT = Decimal("60")
_DEFAULT_VALORES_APROBATORIOS = ["Satisfactorio", "Supera lo esperado"]


class CalificacionError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class CalificacionService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = CalificacionRepository(session=session, tenant_id=self.tenant_id)
        self._umbral_repo = UmbralRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=self.tenant_id)

    async def _resolve_actor(self, auth_user_id: uuid.UUID) -> uuid.UUID:
        usuario = await self._usuario_repo.get_by_auth_user_id(auth_user_id)
        if usuario is None:
            raise CalificacionError("El actor no tiene perfil de usuario en este tenant")
        return usuario.id

    async def _resolve_asignacion(self, usuario_id: uuid.UUID, materia_id: uuid.UUID) -> uuid.UUID:
        asignaciones = await self._asignacion_repo.list(
            usuario_id=usuario_id,
            materia_id=materia_id,
            active_only=True,
        )
        if not asignaciones:
            raise CalificacionError("El docente no tiene una asignación vigente en esta materia")
        return asignaciones[0].id

    def _derive_aprobado(
        self,
        nota_numerica: float | None,
        nota_textual: str | None,
        umbral_pct: Decimal,
        valores_aprobatorios: list[str],
    ) -> bool:
        if nota_numerica is not None:
            return Decimal(str(nota_numerica)) >= umbral_pct
        if nota_textual is not None:
            return nota_textual in valores_aprobatorios
        return False

    def _hash_email(self, email: str) -> str:
        secret = get_settings().secret_key.encode("utf-8")
        return hmac.new(secret, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()

    async def preview(
        self,
        *,
        content: bytes,
        filename: str,
    ) -> PreviewResponse:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        resultado = detectar_actividades(content, ext)
        return PreviewResponse(
            actividades_numericas=resultado["actividades_numericas"],
            actividades_textuales=resultado["actividades_textuales"],
        )

    async def importar(
        self,
        *,
        auth_user_id: uuid.UUID,
        materia_id: uuid.UUID,
        actividades_seleccionadas: list[str],
        content: bytes,
        filename: str,
        ip: str | None = None,
    ) -> ImportarResponse:
        actor_id = await self._resolve_actor(auth_user_id)
        asignacion_id = await self._resolve_asignacion(actor_id, materia_id)

        umbral = await self._umbral_repo.get_by_asignacion(asignacion_id, materia_id)
        umbral_pct = umbral.umbral_pct if umbral else _DEFAULT_UMBRAL_PCT
        valores_aprobatorios = umbral.valores_aprobatorios if umbral else _DEFAULT_VALORES_APROBATORIOS

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        filas = extraer_calificaciones(content, ext, actividades_seleccionadas)

        rows_to_upsert: list[dict] = []
        for fila in filas:
            email_hash = self._hash_email(fila["email"])
            stmt = (
                select(EntradaPadron)
                .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
                .where(EntradaPadron.tenant_id == self.tenant_id)
                .where(EntradaPadron.email_hash == email_hash)
                .where(VersionPadron.materia_id == materia_id)
                .where(VersionPadron.activa.is_(True))
                .where(EntradaPadron.deleted_at.is_(None))
            )
            entrada = await self.session.scalar(stmt)
            if entrada is None:
                continue

            aprobado = self._derive_aprobado(
                fila["nota_numerica"],
                fila["nota_textual"],
                umbral_pct,
                valores_aprobatorios,
            )
            rows_to_upsert.append({
                "entrada_padron_id": entrada.id,
                "actor_id": actor_id,
                "actividad": fila["actividad"],
                "nota_numerica": fila["nota_numerica"],
                "nota_textual": fila["nota_textual"],
                "aprobado": aprobado,
                "origen": "Importado",
            })

        count = await self._repo.upsert_bulk(rows_to_upsert)

        await audit_action(
            session=self.session,
            actor_id=auth_user_id,
            tenant_id=self.tenant_id,
            accion="CALIFICACIONES_IMPORTAR",
            detalle={"materia_id": str(materia_id), "actividades": actividades_seleccionadas},
            materia_id=materia_id,
            filas_afectadas=count,
            ip=ip,
        )

        return ImportarResponse(calificaciones_importadas=count)

    async def reporte_finalizacion(
        self,
        *,
        version_id: uuid.UUID,
        actividades_textuales: list[str],
    ) -> ReporteFinalizacionResponse:
        sin_calificar_raw = await self._repo.get_sin_calificar_textual(
            version_id=version_id,
            actividades_textuales=actividades_textuales,
        )
        items = [
            SinCalificarItem(
                entrada_padron_id=r["entrada_padron_id"],
                nombre=r["nombre"],
                apellidos=r["apellidos"],
                actividad=r["actividad"],
            )
            for r in sin_calificar_raw
        ]
        return ReporteFinalizacionResponse(sin_calificar=items)

    async def vaciar(
        self,
        *,
        auth_user_id: uuid.UUID,
        materia_id: uuid.UUID,
        ip: str | None = None,
    ) -> VaciadoResponse:
        actor_id = await self._resolve_actor(auth_user_id)
        count = await self._repo.delete_by_actor_materia(actor_id, materia_id)

        await audit_action(
            session=self.session,
            actor_id=auth_user_id,
            tenant_id=self.tenant_id,
            accion="CALIFICACIONES_IMPORTAR",
            detalle={"operacion": "vaciado", "materia_id": str(materia_id)},
            materia_id=materia_id,
            filas_afectadas=count,
            ip=ip,
        )

        return VaciadoResponse(eliminadas=count)


class UmbralService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = UmbralRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=self.tenant_id)

    async def _resolve_actor(self, auth_user_id: uuid.UUID) -> uuid.UUID:
        usuario = await self._usuario_repo.get_by_auth_user_id(auth_user_id)
        if usuario is None:
            raise CalificacionError("El actor no tiene perfil de usuario en este tenant")
        return usuario.id

    async def _resolve_asignacion(self, usuario_id: uuid.UUID, materia_id: uuid.UUID) -> uuid.UUID:
        asignaciones = await self._asignacion_repo.list(
            usuario_id=usuario_id,
            materia_id=materia_id,
            active_only=True,
        )
        if not asignaciones:
            raise CalificacionError("El docente no tiene una asignación vigente en esta materia")
        return asignaciones[0].id

    async def get_umbral(
        self,
        *,
        auth_user_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> UmbralResponse:
        actor_id = await self._resolve_actor(auth_user_id)
        asignacion_id = await self._resolve_asignacion(actor_id, materia_id)
        umbral = await self._repo.get_by_asignacion(asignacion_id, materia_id)
        if umbral is None:
            return UmbralResponse(
                umbral_pct=_DEFAULT_UMBRAL_PCT,
                valores_aprobatorios=_DEFAULT_VALORES_APROBATORIOS,
                es_defecto=True,
            )
        return UmbralResponse(
            umbral_pct=umbral.umbral_pct,
            valores_aprobatorios=umbral.valores_aprobatorios,
            es_defecto=False,
        )

    async def set_umbral(
        self,
        *,
        auth_user_id: uuid.UUID,
        materia_id: uuid.UUID,
        request: UmbralRequest,
    ) -> UmbralResponse:
        actor_id = await self._resolve_actor(auth_user_id)
        asignacion_id = await self._resolve_asignacion(actor_id, materia_id)
        umbral = await self._repo.upsert(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=float(request.umbral_pct),
            valores_aprobatorios=request.valores_aprobatorios,
        )
        return UmbralResponse(
            umbral_pct=umbral.umbral_pct,
            valores_aprobatorios=umbral.valores_aprobatorios,
            es_defecto=False,
        )
