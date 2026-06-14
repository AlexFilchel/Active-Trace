from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.avisos import AcknowledgmentAviso, Aviso
from app.repositories.tenant_scoped import TenantScopedRepository


class AvisoRepository(TenantScopedRepository[Aviso]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Aviso, tenant_id=tenant_id)

    async def list_activos_vigentes(self, now: datetime) -> list[Aviso]:
        """Return active avisos within their validity window."""
        stmt = (
            self._base_query()
            .where(Aviso.activo.is_(True))
            .where(Aviso.inicio_en <= now)
            .where(Aviso.fin_en >= now)
            .order_by(Aviso.orden.asc(), Aviso.inicio_en.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())


class AckRepository(TenantScopedRepository[AcknowledgmentAviso]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=AcknowledgmentAviso, tenant_id=tenant_id)

    async def existe(self, aviso_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        result = await self.session.scalar(
            select(AcknowledgmentAviso)
            .where(AcknowledgmentAviso.tenant_id == self.context.tenant_id)
            .where(AcknowledgmentAviso.deleted_at.is_(None))
            .where(AcknowledgmentAviso.aviso_id == aviso_id)
            .where(AcknowledgmentAviso.usuario_id == usuario_id)
        )
        return result is not None

    async def count_by_aviso(self, aviso_id: uuid.UUID) -> int:
        result = await self.session.scalar(
            select(func.count(AcknowledgmentAviso.id))
            .where(AcknowledgmentAviso.tenant_id == self.context.tenant_id)
            .where(AcknowledgmentAviso.deleted_at.is_(None))
            .where(AcknowledgmentAviso.aviso_id == aviso_id)
        )
        return result or 0
