from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class SlotEncuentro(TenantScopedMixin, Base):
    """Plantilla de recurrencia para encuentros sincrónicos."""

    __tablename__ = "slot_encuentro"
    __table_args__ = (
        Index("ix_slot_encuentro_materia_id", "materia_id"),
    )

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=lunes … 6=domingo
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    cant_semanas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha_unica: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
    meet_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    vig_desde: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
    vig_hasta: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)


class InstanciaEncuentro(TenantScopedMixin, Base):
    """Encuentro concreto, derivado de un slot o independiente."""

    __tablename__ = "instancia_encuentro"
    __table_args__ = (
        Index("ix_instancia_encuentro_materia_id", "materia_id"),
        Index("ix_instancia_encuentro_slot_id", "slot_id"),
    )

    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("slot_encuentro.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Programado")
    meet_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


class Guardia(TenantScopedMixin, Base):
    """Registro de guardia de atención a alumnos."""

    __tablename__ = "guardia"
    __table_args__ = (
        Index("ix_guardia_materia_id", "materia_id"),
    )

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
    )
    carrera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dia: Mapped[date] = mapped_column(Date, nullable=False)
    horario: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Pendiente")
    comentarios: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    creada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
