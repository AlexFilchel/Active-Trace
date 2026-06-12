from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class Calificacion(TenantScopedMixin, Base):
    __tablename__ = "calificacion"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entrada_padron_id", "actividad", "actor_id", name="uq_calificacion_entrada_actividad_actor"),
    )

    entrada_padron_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entrada_padron.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False, index=True)
    actividad: Mapped[str] = mapped_column(String(300), nullable=False)
    nota_numerica: Mapped[Decimal | None] = mapped_column(Numeric(precision=10, scale=4), nullable=True, default=None)
    nota_textual: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    aprobado: Mapped[bool] = mapped_column(Boolean, nullable=False)
    origen: Mapped[str] = mapped_column(String(50), nullable=False, default="Importado")


class UmbralMateria(TenantScopedMixin, Base):
    __tablename__ = "umbral_materia"
    __table_args__ = (
        UniqueConstraint("tenant_id", "asignacion_id", "materia_id", name="uq_umbral_materia_asignacion"),
    )

    asignacion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("asignacion.id", ondelete="CASCADE"), nullable=False, index=True)
    materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False, index=True)
    umbral_pct: Mapped[Decimal] = mapped_column(Numeric(precision=5, scale=2), nullable=False, default=Decimal("60"))
    valores_aprobatorios: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=lambda: ["Satisfactorio", "Supera lo esperado"],
    )
