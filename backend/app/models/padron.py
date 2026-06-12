from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class VersionPadron(TenantScopedMixin, Base):
    __tablename__ = "version_padron"
    __table_args__ = (
        # Only one active version per (tenant, materia, cohorte) at a time
        Index(
            "uq_version_padron_activa",
            "tenant_id",
            "materia_id",
            "cohorte_id",
            unique=True,
            postgresql_where=text("activa = true"),
        ),
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False)
    cohorte_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=False)
    cargado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    cargado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EntradaPadron(TenantScopedMixin, Base):
    __tablename__ = "entrada_padron"

    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("version_padron.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(200), nullable=False)
    email_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    comision: Mapped[str | None] = mapped_column(String(200), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(200), nullable=True)
