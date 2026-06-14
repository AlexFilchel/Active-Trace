from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UuidLifecycleMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


class TenantScopedMixin(UuidLifecycleMixin):
    @declared_attr.directive
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True)


class Tenant(UuidLifecycleMixin, Base):
    __tablename__ = "tenant"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    comunicaciones_aprobacion_requerida: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    comunicaciones_aprobacion_masiva: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    moodle_ws_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    moodle_ws_token_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
