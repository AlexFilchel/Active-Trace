from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tareas import ComentarioTarea, Tarea
from app.repositories.tenant_scoped import TenantScopedRepository


class TareaRepository(TenantScopedRepository[Tarea]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Tarea, tenant_id=tenant_id)

    async def list_mis_tareas(
        self,
        usuario_id: uuid.UUID,
        estado: str | None = None,
        materia_id: uuid.UUID | None = None,
    ) -> list[Tarea]:
        stmt = self._base_query().where(
            or_(Tarea.asignado_a == usuario_id, Tarea.asignado_por == usuario_id)
        )
        if estado is not None:
            stmt = stmt.where(Tarea.estado == estado)
        if materia_id is not None:
            stmt = stmt.where(Tarea.materia_id == materia_id)
        result = await self.session.scalars(stmt.order_by(Tarea.created_at.desc()))
        return list(result.all())

    async def list_admin(
        self,
        asignado_a: uuid.UUID | None = None,
        asignado_por: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        estado: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Tarea]:
        stmt = self._base_query()
        if asignado_a is not None:
            stmt = stmt.where(Tarea.asignado_a == asignado_a)
        if asignado_por is not None:
            stmt = stmt.where(Tarea.asignado_por == asignado_por)
        if materia_id is not None:
            stmt = stmt.where(Tarea.materia_id == materia_id)
        if estado is not None:
            stmt = stmt.where(Tarea.estado == estado)
        stmt = stmt.order_by(Tarea.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())


class ComentarioTareaRepository(TenantScopedRepository[ComentarioTarea]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=ComentarioTarea, tenant_id=tenant_id)

    async def list_by_tarea(self, tarea_id: uuid.UUID) -> list[ComentarioTarea]:
        stmt = (
            select(ComentarioTarea)
            .where(ComentarioTarea.tenant_id == self.context.tenant_id)
            .where(ComentarioTarea.deleted_at.is_(None))
            .where(ComentarioTarea.tarea_id == tarea_id)
            .order_by(ComentarioTarea.comentado_at.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
