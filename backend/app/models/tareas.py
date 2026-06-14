from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin, utc_now


class Tarea(TenantScopedMixin, Base):
    __tablename__ = "tarea"
    __table_args__ = (
        Index("ix_tarea_asignado_a", "asignado_a"),
        Index("ix_tarea_asignado_por", "asignado_por"),
        Index("ix_tarea_materia_id", "materia_id"),
        Index("ix_tarea_estado", "estado"),
    )

    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
    )
    asignado_a: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asignado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Pendiente")
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    contexto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        default=None,
    )


class ComentarioTarea(TenantScopedMixin, Base):
    __tablename__ = "comentario_tarea"
    __table_args__ = (
        Index("ix_comentario_tarea_tarea_id", "tarea_id"),
    )

    tarea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tarea.id", ondelete="CASCADE"),
        nullable=False,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    comentado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
