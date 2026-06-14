from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.models.avisos import AcknowledgmentAviso
from app.repositories.avisos import AckRepository, AvisoRepository
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository
from app.schemas.avisos import (
    AckResponse,
    AvisoGestionResponse,
    AvisoResponse,
    CrearAvisoRequest,
    EditarAvisoRequest,
    MetricasAvisoResponse,
)


class AvisoNotFoundError(Exception):
    status_code = 404

    def __init__(self, detail: str = "Aviso no encontrado.") -> None:
        self.detail = detail
        super().__init__(detail)


class AvisoAckInvalidoError(Exception):
    status_code = 422

    def __init__(self, detail: str = "El aviso no puede acusarse.") -> None:
        self.detail = detail
        super().__init__(detail)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AvisoService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._aviso_repo = AvisoRepository(session=session, tenant_id=self.tenant_id)
        self._ack_repo = AckRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=self.tenant_id)

    async def _resolve_usuario(self, auth_user_id: uuid.UUID) -> uuid.UUID:
        usuario = await self._usuario_repo.get_by_auth_user_id(auth_user_id)
        if usuario is None:
            raise AvisoNotFoundError("El usuario no tiene perfil en este tenant.")
        return usuario.id

    async def _get_contexto_usuario(self, usuario_id: uuid.UUID) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
        """Return (materia_ids, cohorte_ids) from active asignaciones."""
        asignaciones = await self._asignacion_repo.list_vigentes_for_user(usuario_id)
        materia_ids = {a.materia_id for a in asignaciones if a.materia_id}
        cohorte_ids = {a.cohorte_id for a in asignaciones if a.cohorte_id}
        return materia_ids, cohorte_ids

    def _audiencia_incluye(
        self,
        aviso,
        roles: list[str],
        materia_ids: set[uuid.UUID],
        cohorte_ids: set[uuid.UUID],
    ) -> bool:
        alcance = aviso.alcance
        if alcance == "Global":
            return True
        if alcance == "PorRol":
            return aviso.rol_destino in roles
        if alcance == "PorMateria":
            return aviso.materia_id in materia_ids
        if alcance == "PorCohorte":
            return aviso.cohorte_id in cohorte_ids
        return False

    # -------------------------------------------------------------------------
    # Task 4.2 — Crear aviso
    # -------------------------------------------------------------------------

    async def crear_aviso(
        self,
        *,
        actor_id: uuid.UUID,
        payload: CrearAvisoRequest,
        ip: str | None = None,
    ) -> AvisoResponse:
        aviso = await self._aviso_repo.create(
            alcance=payload.alcance,
            materia_id=payload.materia_id,
            cohorte_id=payload.cohorte_id,
            rol_destino=payload.rol_destino,
            severidad=payload.severidad,
            titulo=payload.titulo,
            cuerpo=payload.cuerpo,
            inicio_en=payload.inicio_en,
            fin_en=payload.fin_en,
            orden=payload.orden,
            activo=payload.activo,
            requiere_ack=payload.requiere_ack,
        )
        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="AVISO_CREAR",
            filas_afectadas=1,
            detalle={"aviso_id": str(aviso.id), "titulo": aviso.titulo},
            ip=ip,
        )
        return AvisoResponse.model_validate(aviso, from_attributes=True).model_copy(update={"acusado": False})

    # -------------------------------------------------------------------------
    # Task 4.3 — Editar aviso
    # -------------------------------------------------------------------------

    async def editar_aviso(
        self,
        *,
        actor_id: uuid.UUID,
        aviso_id: uuid.UUID,
        payload: EditarAvisoRequest,
        ip: str | None = None,
    ) -> AvisoResponse:
        aviso = await self._aviso_repo.get(aviso_id)
        if aviso is None:
            raise AvisoNotFoundError()
        updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
        for field, value in updates.items():
            setattr(aviso, field, value)
        await self.session.flush()
        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="AVISO_EDITAR",
            filas_afectadas=1,
            detalle={"aviso_id": str(aviso_id)},
            ip=ip,
        )
        return AvisoResponse.model_validate(aviso, from_attributes=True).model_copy(update={"acusado": False})

    # -------------------------------------------------------------------------
    # Task 4.4 — Listar gestión
    # -------------------------------------------------------------------------

    async def listar_gestion(self) -> list[AvisoGestionResponse]:
        avisos = await self._aviso_repo.list(include_deleted=False)
        result = []
        for aviso in avisos:
            total_acks = await self._ack_repo.count_by_aviso(aviso.id)
            result.append(
                AvisoGestionResponse.model_validate(aviso, from_attributes=True).model_copy(update={"acusado": False, "total_acks": total_acks})
            )
        return result

    # -------------------------------------------------------------------------
    # Task 4.5 — Listar mis avisos
    # -------------------------------------------------------------------------

    async def listar_mis_avisos(
        self,
        *,
        auth_user_id: uuid.UUID,
        roles: list[str],
        incluir_acusados: bool = False,
    ) -> list[AvisoResponse]:
        usuario_id = await self._resolve_usuario(auth_user_id)
        materia_ids, cohorte_ids = await self._get_contexto_usuario(usuario_id)
        now = _utc_now()
        avisos = await self._aviso_repo.list_activos_vigentes(now)

        result = []
        for aviso in avisos:
            if not self._audiencia_incluye(aviso, roles, materia_ids, cohorte_ids):
                continue
            acusado = await self._ack_repo.existe(aviso.id, usuario_id)
            if aviso.requiere_ack and acusado and not incluir_acusados:
                continue
            result.append(AvisoResponse.model_validate(aviso, from_attributes=True).model_copy(update={"acusado": acusado}))
        return result

    # -------------------------------------------------------------------------
    # Task 4.6 — Ack
    # -------------------------------------------------------------------------

    async def ack(
        self,
        *,
        auth_user_id: uuid.UUID,
        aviso_id: uuid.UUID,
        ip: str | None = None,
    ) -> tuple[AckResponse, bool]:
        """Returns (AckResponse, created: bool). created=False means idempotent."""
        aviso = await self._aviso_repo.get(aviso_id)
        if aviso is None:
            raise AvisoNotFoundError()
        now = _utc_now()
        if not aviso.activo:
            raise AvisoAckInvalidoError("El aviso no está activo.")
        if not (aviso.inicio_en <= now <= aviso.fin_en):
            raise AvisoAckInvalidoError("El aviso está fuera de su ventana de vigencia.")
        if not aviso.requiere_ack:
            raise AvisoAckInvalidoError("Este aviso no requiere confirmación de lectura.")

        usuario_id = await self._resolve_usuario(auth_user_id)

        ya_existia = await self._ack_repo.existe(aviso_id, usuario_id)
        if ya_existia:
            ack_row = await self.session.scalar(
                select(AcknowledgmentAviso)
                .where(AcknowledgmentAviso.tenant_id == self.tenant_id)
                .where(AcknowledgmentAviso.deleted_at.is_(None))
                .where(AcknowledgmentAviso.aviso_id == aviso_id)
                .where(AcknowledgmentAviso.usuario_id == usuario_id)
            )
            return (
                AckResponse(
                    aviso_id=aviso_id,
                    usuario_id=usuario_id,
                    confirmado_at=ack_row.confirmado_at,
                    ya_existia=True,
                ),
                False,
            )

        ack_row = await self._ack_repo.create(
            aviso_id=aviso_id,
            usuario_id=usuario_id,
            confirmado_at=now,
        )
        await audit_action(
            session=self.session,
            actor_id=auth_user_id,
            tenant_id=self.tenant_id,
            accion="AVISO_ACK",
            filas_afectadas=1,
            detalle={"aviso_id": str(aviso_id)},
            ip=ip,
        )
        return (
            AckResponse(
                aviso_id=aviso_id,
                usuario_id=usuario_id,
                confirmado_at=ack_row.confirmado_at,
                ya_existia=False,
            ),
            True,
        )

    # -------------------------------------------------------------------------
    # Task 4.7 — Métricas
    # -------------------------------------------------------------------------

    async def metricas(self, aviso_id: uuid.UUID) -> MetricasAvisoResponse:
        aviso = await self._aviso_repo.get(aviso_id)
        if aviso is None:
            raise AvisoNotFoundError()
        total_acks = await self._ack_repo.count_by_aviso(aviso_id)
        return MetricasAvisoResponse(
            aviso_id=aviso_id,
            titulo=aviso.titulo,
            requiere_ack=aviso.requiere_ack,
            total_acks=total_acks,
        )
