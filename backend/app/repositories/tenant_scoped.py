from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import TenantContextError, TenantContext, ensure_tenant_context
from app.models import TenantScopedMixin


ModelT = TypeVar("ModelT", bound=TenantScopedMixin)


class TenantScopedRepository(Generic[ModelT]):
    def __init__(self, *, session: AsyncSession, model: type[ModelT], tenant_id: uuid.UUID | str | None):
        self.session = session
        self.model = model
        self.context: TenantContext = ensure_tenant_context(tenant_id)

    def _base_query(self, *, include_deleted: bool = False) -> Select[tuple[ModelT]]:
        statement = select(self.model).where(self.model.tenant_id == self.context.tenant_id)

        if not include_deleted:
            statement = statement.where(self.model.deleted_at.is_(None))

        return statement

    async def create(self, **values: Any) -> ModelT:
        entity = self.model(**values, tenant_id=self.context.tenant_id)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list(self, *, include_deleted: bool = False) -> list[ModelT]:
        result = await self.session.scalars(self._base_query(include_deleted=include_deleted))
        return list(result.all())

    async def get(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        statement = self._base_query(include_deleted=include_deleted).where(self.model.id == entity_id)
        return await self.session.scalar(statement)

    async def update(self, entity_id: uuid.UUID, **values: Any) -> ModelT | None:
        entity = await self.get(entity_id, include_deleted=True)

        if entity is None:
            return None

        for field_name, value in values.items():
            setattr(entity, field_name, value)

        await self.session.flush()
        return entity

    async def soft_delete(self, entity_id: uuid.UUID) -> bool:
        entity = await self.get(entity_id, include_deleted=True)

        if entity is None or entity.deleted_at is not None:
            return False

        from app.models.base import utc_now

        entity.deleted_at = utc_now()
        await self.session.flush()
        return True
