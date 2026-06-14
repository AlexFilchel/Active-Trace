from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditoriaRepository:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id

    def _base(self):
        return select(AuditLog).where(AuditLog.tenant_id == self.tenant_id)

    async def acciones_por_dia(
        self,
        actor_id: uuid.UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
    ) -> list[dict]:
        fecha_col = func.date(AuditLog.fecha_hora).label("fecha")
        stmt = (
            select(fecha_col, func.count().label("total"))
            .where(AuditLog.tenant_id == self.tenant_id)
        )
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if desde is not None:
            stmt = stmt.where(func.date(AuditLog.fecha_hora) >= desde)
        if hasta is not None:
            stmt = stmt.where(func.date(AuditLog.fecha_hora) <= hasta)
        if materia_id is not None:
            stmt = stmt.where(AuditLog.materia_id == materia_id)
        stmt = stmt.group_by(fecha_col).order_by(fecha_col)
        result = await self.session.execute(stmt)
        return [{"fecha": row.fecha, "total": row.total} for row in result.all()]

    async def estado_comunicaciones(
        self,
        actor_id: uuid.UUID | None = None,
    ) -> list[dict]:
        stmt = (
            select(
                AuditLog.actor_id,
                AuditLog.accion,
                func.count().label("total"),
            )
            .where(AuditLog.tenant_id == self.tenant_id)
            .where(AuditLog.accion.like("COMUNICACION_%"))
        )
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        stmt = stmt.group_by(AuditLog.actor_id, AuditLog.accion).order_by(AuditLog.actor_id)
        result = await self.session.execute(stmt)
        return [
            {"actor_id": row.actor_id, "accion": row.accion, "total": row.total}
            for row in result.all()
        ]

    async def interacciones_docente(
        self,
        actor_id: uuid.UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
    ) -> list[dict]:
        stmt = (
            select(
                AuditLog.actor_id,
                AuditLog.accion,
                func.count().label("total"),
            )
            .where(AuditLog.tenant_id == self.tenant_id)
        )
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if desde is not None:
            stmt = stmt.where(func.date(AuditLog.fecha_hora) >= desde)
        if hasta is not None:
            stmt = stmt.where(func.date(AuditLog.fecha_hora) <= hasta)
        if materia_id is not None:
            stmt = stmt.where(AuditLog.materia_id == materia_id)
        stmt = (
            stmt.group_by(AuditLog.actor_id, AuditLog.accion)
            .order_by(func.count().desc())
        )
        result = await self.session.execute(stmt)
        return [
            {"actor_id": row.actor_id, "accion": row.accion, "total": row.total}
            for row in result.all()
        ]

    async def log(
        self,
        actor_id: uuid.UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        accion: str | None = None,
        limit: int = 200,
    ) -> list[AuditLog]:
        stmt = self._base()
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if desde is not None:
            stmt = stmt.where(func.date(AuditLog.fecha_hora) >= desde)
        if hasta is not None:
            stmt = stmt.where(func.date(AuditLog.fecha_hora) <= hasta)
        if accion is not None:
            stmt = stmt.where(AuditLog.accion == accion)
        stmt = stmt.order_by(AuditLog.fecha_hora.desc()).limit(min(limit, 500))
        result = await self.session.scalars(stmt)
        return list(result.all())
