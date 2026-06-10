"""Append-only repository for AuditLog.

Design decisions (from design.md D1, D2):
- Does NOT extend TenantScopedRepository because that exposes update/soft_delete.
- Only exposes create(), get(), and list() — no mutation methods.
- Filters by tenant_id on all read operations (multi-tenancy row-level).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditLogRepository:
    """Repository for AuditLog — append-only, no update or delete."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id))

    async def create(self, **values: Any) -> AuditLog:
        """Create and flush a new AuditLog entry."""
        entry = AuditLog(**values, tenant_id=self.tenant_id)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get(self, entry_id: uuid.UUID) -> AuditLog | None:
        """Return a single AuditLog entry scoped to this tenant."""
        statement = (
            select(AuditLog)
            .where(AuditLog.tenant_id == self.tenant_id)
            .where(AuditLog.id == entry_id)
        )
        return await self.session.scalar(statement)

    async def list(self) -> list[AuditLog]:
        """Return all AuditLog entries for this tenant, newest first."""
        statement = (
            select(AuditLog)
            .where(AuditLog.tenant_id == self.tenant_id)
            .order_by(AuditLog.fecha_hora.desc())
        )
        result = await self.session.scalars(statement)
        return list(result.all())
