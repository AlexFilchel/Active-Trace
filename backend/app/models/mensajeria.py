from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin, utc_now


class HiloMensaje(TenantScopedMixin, Base):
    __tablename__ = "hilo_mensaje"
    __table_args__ = (
        Index("ix_hilo_mensaje_creado_por", "creado_por"),
    )

    asunto: Mapped[str] = mapped_column(String(200), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )


class MensajeInterno(TenantScopedMixin, Base):
    __tablename__ = "mensaje_interno"
    __table_args__ = (
        Index("ix_mensaje_interno_hilo_id", "hilo_id"),
        Index("ix_mensaje_interno_destinatario_leido", "tenant_id", "destinatario_id", "leido"),
    )

    hilo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hilo_mensaje.id", ondelete="CASCADE"),
        nullable=False,
    )
    remitente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    leido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
