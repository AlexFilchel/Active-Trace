from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin, utc_now


class Aviso(TenantScopedMixin, Base):
    """Notificación institucional segmentada por alcance, rol, materia o cohorte."""

    __tablename__ = "aviso"
    __table_args__ = (
        Index("ix_aviso_materia_id", "materia_id"),
        Index("ix_aviso_cohorte_id", "cohorte_id"),
        Index("ix_aviso_inicio_en", "inicio_en"),
    )

    alcance: Mapped[str] = mapped_column(String(20), nullable=False)
    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
    )
    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
    )
    rol_destino: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    severidad: Mapped[str] = mapped_column(String(20), nullable=False, default="Info")
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    inicio_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requiere_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AcknowledgmentAviso(TenantScopedMixin, Base):
    """Acuse de recibo de un aviso por parte de un usuario."""

    __tablename__ = "acknowledgment_aviso"
    __table_args__ = (
        Index("ix_ack_aviso_aviso_id", "aviso_id"),
        Index("ix_ack_aviso_usuario_id", "usuario_id"),
        UniqueConstraint("tenant_id", "aviso_id", "usuario_id", name="uq_ack_aviso_tenant_aviso_usuario"),
    )

    aviso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aviso.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confirmado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
