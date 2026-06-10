"""Audit log model.

Design decisions (from design.md):
- D1: Append-only enforcement at app level — no updated_at, no deleted_at.
- D2: AuditMixin is separate from TenantScopedMixin (which carries updated_at/deleted_at).
- Model is immutable by design; AuditLogRepository only exposes create + read.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditMixin:
    """Minimal mixin for immutable audit records.

    Intentionally omits updated_at and deleted_at — audit records are
    append-only and must never be modified or logically deleted.
    """

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    @declared_attr.directive
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True)


class AuditLog(AuditMixin, Base):
    """Immutable record of a significant action in the system (E-AUD).

    Every field except the required ones is nullable to allow partial context.
    The trigger audit_log_immutable (created in migration 004) enforces
    append-only at DB level by rejecting UPDATE and DELETE.
    """

    __tablename__ = "audit_log"

    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    impersonado_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_user.id", ondelete="RESTRICT"),
        nullable=True,
    )
    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    accion: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    detalle: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    filas_afectadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
