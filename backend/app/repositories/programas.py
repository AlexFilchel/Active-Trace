from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programas import FechaAcademica, ProgramaMateria
from app.repositories.tenant_scoped import TenantScopedRepository


class ProgramaRepository(TenantScopedRepository[ProgramaMateria]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=ProgramaMateria, tenant_id=tenant_id)

    async def list_filtrado(
        self,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[ProgramaMateria]:
        stmt = self._base_query()
        if materia_id is not None:
            stmt = stmt.where(ProgramaMateria.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(ProgramaMateria.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(ProgramaMateria.cohorte_id == cohorte_id)
        result = await self.session.scalars(stmt.order_by(ProgramaMateria.cargado_at.desc()))
        return list(result.all())


class FechaAcademicaRepository(TenantScopedRepository[FechaAcademica]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=FechaAcademica, tenant_id=tenant_id)

    async def list_filtrado(
        self,
        materia_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        tipo: str | None = None,
        periodo: str | None = None,
    ) -> list[FechaAcademica]:
        stmt = self._base_query()
        if materia_id is not None:
            stmt = stmt.where(FechaAcademica.materia_id == materia_id)
        if cohorte_id is not None:
            stmt = stmt.where(FechaAcademica.cohorte_id == cohorte_id)
        if tipo is not None:
            stmt = stmt.where(FechaAcademica.tipo == tipo)
        if periodo is not None:
            stmt = stmt.where(FechaAcademica.periodo == periodo)
        result = await self.session.scalars(stmt.order_by(FechaAcademica.fecha.asc()))
        return list(result.all())
