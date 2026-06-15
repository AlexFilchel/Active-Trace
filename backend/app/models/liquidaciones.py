from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, Numeric, String, Text, UniqueConstraint
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin, utc_now


class SalarioBase(TenantScopedMixin, Base):
    __tablename__ = "salario_base"

    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)


class SalarioPlus(TenantScopedMixin, Base):
    __tablename__ = "salario_plus"

    grupo: Mapped[str] = mapped_column(String(50), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)


class Liquidacion(TenantScopedMixin, Base):
    __tablename__ = "liquidacion"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "cohorte_id", "periodo", "usuario_id", "rol",
            name="uq_liquidacion_periodo_docente_rol",
        ),
    )

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    periodo: Mapped[str] = mapped_column(String(7), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    comisiones: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    monto_base: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    monto_plus: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    es_nexo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluido_por_factura: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="Abierta")


class Factura(TenantScopedMixin, Base):
    __tablename__ = "factura"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    periodo: Mapped[str] = mapped_column(String(7), nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    referencia_archivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    tamano_kb: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="Pendiente")
    cargada_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    abonada_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
