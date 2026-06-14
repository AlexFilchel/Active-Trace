from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encuentros import Guardia, InstanciaEncuentro, SlotEncuentro
from app.repositories.tenant_scoped import TenantScopedRepository


class SlotEncuentroRepository(TenantScopedRepository[SlotEncuentro]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=SlotEncuentro, tenant_id=tenant_id)

    # create and get are inherited from TenantScopedRepository


class InstanciaEncuentroRepository(TenantScopedRepository[InstanciaEncuentro]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=InstanciaEncuentro, tenant_id=tenant_id)

    async def bulk_create(self, instancias: list[InstanciaEncuentro]) -> list[InstanciaEncuentro]:
        """Insert multiple instancias in a single flush."""
        for inst in instancias:
            self.session.add(inst)
        await self.session.flush()
        return instancias

    async def list_filtered(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        estado: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[InstanciaEncuentro]:
        stmt = self._base_query().order_by(InstanciaEncuentro.fecha.asc())
        if materia_id is not None:
            stmt = stmt.where(InstanciaEncuentro.materia_id == materia_id)
        if estado is not None:
            stmt = stmt.where(InstanciaEncuentro.estado == estado)
        if desde is not None:
            stmt = stmt.where(InstanciaEncuentro.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(InstanciaEncuentro.fecha <= hasta)
        # cohorte_id filter requires join to slot → filtering done at service layer
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_materia(self, materia_id: uuid.UUID) -> list[InstanciaEncuentro]:
        """Return instancias for a materia ordered by fecha ascending."""
        stmt = (
            self._base_query()
            .where(InstanciaEncuentro.materia_id == materia_id)
            .order_by(InstanciaEncuentro.fecha.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    # get and update are inherited from TenantScopedRepository


class GuardiaRepository(TenantScopedRepository[Guardia]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Guardia, tenant_id=tenant_id)

    async def list_filtered(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        estado: str | None = None,
    ) -> list[Guardia]:
        stmt = self._base_query().order_by(Guardia.dia.asc())
        if materia_id is not None:
            stmt = stmt.where(Guardia.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(Guardia.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(Guardia.cohorte_id == cohorte_id)
        if estado is not None:
            stmt = stmt.where(Guardia.estado == estado)
        result = await self.session.scalars(stmt)
        return list(result.all())
