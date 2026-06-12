from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import UmbralMateria
from app.repositories.tenant_scoped import TenantScopedRepository


class UmbralRepository(TenantScopedRepository[UmbralMateria]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=UmbralMateria, tenant_id=tenant_id)

    async def get_by_asignacion(
        self,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> UmbralMateria | None:
        stmt = (
            select(UmbralMateria)
            .where(UmbralMateria.tenant_id == self.context.tenant_id)
            .where(UmbralMateria.asignacion_id == asignacion_id)
            .where(UmbralMateria.materia_id == materia_id)
            .where(UmbralMateria.deleted_at.is_(None))
        )
        return await self.session.scalar(stmt)

    async def upsert(
        self,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        umbral_pct: float,
        valores_aprobatorios: list[str],
    ) -> UmbralMateria:
        stmt = (
            insert(UmbralMateria)
            .values(
                tenant_id=self.context.tenant_id,
                asignacion_id=asignacion_id,
                materia_id=materia_id,
                umbral_pct=umbral_pct,
                valores_aprobatorios=valores_aprobatorios,
            )
            .on_conflict_do_update(
                constraint="uq_umbral_materia_asignacion",
                set_={
                    "umbral_pct": umbral_pct,
                    "valores_aprobatorios": valores_aprobatorios,
                    "updated_at": text("now()"),
                },
            )
            .returning(UmbralMateria)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        return row
