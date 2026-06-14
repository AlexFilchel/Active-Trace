from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class Evaluacion(TenantScopedMixin, Base):
    """Convocatoria de coloquio (materia, cohorte, tipo, instancia, días y estado)."""

    __tablename__ = "evaluacion"
    __table_args__ = (
        Index("ix_evaluacion_materia_id", "materia_id"),
        Index("ix_evaluacion_cohorte_id", "cohorte_id"),
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, default="Coloquio")
    instancia: Mapped[str] = mapped_column(String(255), nullable=False)
    dias_disponibles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Abierta")


class DiaEvaluacion(TenantScopedMixin, Base):
    """Un día reservable de una convocatoria con su cupo total."""

    __tablename__ = "dia_evaluacion"
    __table_args__ = (
        Index("ix_dia_evaluacion_evaluacion_id", "evaluacion_id"),
    )

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    cupo_total: Mapped[int] = mapped_column(Integer, nullable=False)


class CandidatoEvaluacion(TenantScopedMixin, Base):
    """Alumno habilitado para reservar turno en una convocatoria."""

    __tablename__ = "candidato_evaluacion"
    __table_args__ = (
        Index("ix_candidato_evaluacion_evaluacion_id", "evaluacion_id"),
    )

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class ReservaEvaluacion(TenantScopedMixin, Base):
    """Turno reservado por un alumno en un día de convocatoria."""

    __tablename__ = "reserva_evaluacion"
    __table_args__ = (
        Index("ix_reserva_evaluacion_evaluacion_id", "evaluacion_id"),
        Index("ix_reserva_evaluacion_dia_id", "dia_evaluacion_id"),
    )

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dia_evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dia_evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fecha_hora: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")


class ResultadoEvaluacion(TenantScopedMixin, Base):
    """Nota final consolidada por alumno en una convocatoria."""

    __tablename__ = "resultado_evaluacion"
    __table_args__ = (
        Index("ix_resultado_evaluacion_evaluacion_id", "evaluacion_id"),
    )

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nota_final: Mapped[str] = mapped_column(String(50), nullable=False)
