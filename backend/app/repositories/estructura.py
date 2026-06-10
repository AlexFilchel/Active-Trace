"""Repositories para la estructura académica: Carrera, Cohorte, Materia."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estructura import Carrera, Cohorte, Materia
from app.repositories.tenant_scoped import TenantScopedRepository


class CarreraRepository(TenantScopedRepository[Carrera]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=Carrera, tenant_id=tenant_id)

    async def get_by_codigo(self, codigo: str) -> Carrera | None:
        stmt = self._base_query().where(Carrera.codigo == codigo)
        return await self.session.scalar(stmt)


class CohorteRepository(TenantScopedRepository[Cohorte]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=Cohorte, tenant_id=tenant_id)

    async def list_by_carrera(self, carrera_id: uuid.UUID) -> list[Cohorte]:
        stmt = self._base_query().where(Cohorte.carrera_id == carrera_id)
        result = await self.session.scalars(stmt)
        return list(result.all())


class MateriaRepository(TenantScopedRepository[Materia]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=Materia, tenant_id=tenant_id)

    async def get_by_codigo(self, codigo: str) -> Materia | None:
        stmt = self._base_query().where(Materia.codigo == codigo)
        return await self.session.scalar(stmt)

    async def list_by_estado(self, estado: str) -> list[Materia]:
        stmt = self._base_query().where(Materia.estado == estado)
        result = await self.session.scalars(stmt)
        return list(result.all())
