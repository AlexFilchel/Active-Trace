from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.padron import EntradaPadron, VersionPadron
from app.repositories.tenant_scoped import TenantScopedRepository


class VersionPadronRepository(TenantScopedRepository[VersionPadron]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=VersionPadron, tenant_id=tenant_id)

    async def get_activa(self, materia_id: uuid.UUID, cohorte_id: uuid.UUID) -> VersionPadron | None:
        stmt = (
            self._base_query()
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .where(VersionPadron.activa.is_(True))
        )
        return await self.session.scalar(stmt)

    async def desactivar_anterior(self, materia_id: uuid.UUID, cohorte_id: uuid.UUID) -> bool:
        stmt = (
            update(VersionPadron)
            .where(VersionPadron.tenant_id == self.context.tenant_id)
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .where(VersionPadron.activa.is_(True))
            .values(activa=False)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def create_version(self, materia_id: uuid.UUID, cohorte_id: uuid.UUID, cargado_por: uuid.UUID) -> VersionPadron:
        version = VersionPadron(
            tenant_id=self.context.tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=cargado_por,
            activa=True,
        )
        self.session.add(version)
        await self.session.flush()
        return version


class EntradaPadronRepository(TenantScopedRepository[EntradaPadron]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=EntradaPadron, tenant_id=tenant_id)

    async def bulk_create(self, entradas: list[EntradaPadron]) -> None:
        self.session.add_all(entradas)
        await self.session.flush()

    async def list_by_version(self, version_id: uuid.UUID) -> list[EntradaPadron]:
        stmt = (
            self._base_query()
            .where(EntradaPadron.version_id == version_id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
