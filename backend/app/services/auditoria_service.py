from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.auditoria import AuditoriaRepository
from app.schemas.auditoria import (
    AccionPorDiaResponse,
    AuditLogResponse,
    EstadoComunicacionResponse,
    InteraccionDocenteResponse,
)

_ROLES_GLOBALES = {"ADMIN", "FINANZAS"}


class AuditoriaService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = AuditoriaRepository(session=session, tenant_id=self.tenant_id)

    def _scope_actor_id(
        self,
        *,
        roles: list[str],
        user_auth_id: uuid.UUID,
        filtro_usuario_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        """D2: COORDINADOR sin rol global → scope propio. ADMIN/FINANZAS → filtro libre."""
        tiene_rol_global = bool(set(roles) & _ROLES_GLOBALES)
        if not tiene_rol_global:
            return user_auth_id
        return filtro_usuario_id

    async def acciones_por_dia(
        self,
        *,
        roles: list[str],
        user_auth_id: uuid.UUID,
        desde: date | None = None,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
        usuario_id: uuid.UUID | None = None,
    ) -> list[AccionPorDiaResponse]:
        actor_id = self._scope_actor_id(
            roles=roles, user_auth_id=user_auth_id, filtro_usuario_id=usuario_id
        )
        rows = await self._repo.acciones_por_dia(
            actor_id=actor_id, desde=desde, hasta=hasta, materia_id=materia_id
        )
        return [AccionPorDiaResponse(fecha=r["fecha"], total=r["total"]) for r in rows]

    async def estado_comunicaciones(
        self,
        *,
        roles: list[str],
        user_auth_id: uuid.UUID,
    ) -> list[EstadoComunicacionResponse]:
        actor_id = self._scope_actor_id(roles=roles, user_auth_id=user_auth_id)
        rows = await self._repo.estado_comunicaciones(actor_id=actor_id)
        return [
            EstadoComunicacionResponse(
                actor_id=r["actor_id"], accion=r["accion"], total=r["total"]
            )
            for r in rows
        ]

    async def interacciones_docente(
        self,
        *,
        roles: list[str],
        user_auth_id: uuid.UUID,
        desde: date | None = None,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
        usuario_id: uuid.UUID | None = None,
    ) -> list[InteraccionDocenteResponse]:
        actor_id = self._scope_actor_id(
            roles=roles, user_auth_id=user_auth_id, filtro_usuario_id=usuario_id
        )
        rows = await self._repo.interacciones_docente(
            actor_id=actor_id, desde=desde, hasta=hasta, materia_id=materia_id
        )
        return [
            InteraccionDocenteResponse(
                actor_id=r["actor_id"], accion=r["accion"], total=r["total"]
            )
            for r in rows
        ]

    async def log(
        self,
        *,
        roles: list[str],
        user_auth_id: uuid.UUID,
        desde: date | None = None,
        hasta: date | None = None,
        accion: str | None = None,
        usuario_id: uuid.UUID | None = None,
        limit: int = 200,
    ) -> list[AuditLogResponse]:
        actor_id = self._scope_actor_id(
            roles=roles, user_auth_id=user_auth_id, filtro_usuario_id=usuario_id
        )
        entries = await self._repo.log(
            actor_id=actor_id, desde=desde, hasta=hasta, accion=accion, limit=limit
        )
        return [AuditLogResponse.model_validate(e, from_attributes=True) for e in entries]
