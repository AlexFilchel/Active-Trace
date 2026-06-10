"""Estructura académica: Carrera, Cohorte, Materia.

Catálogo base del tenant. Una sola fuente de verdad por código (ADR-006).
Estado almacenado como String(20) con validación en schemas Pydantic.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class Carrera(TenantScopedMixin, Base):
    """Programa académico del tenant.

    Unicidad: (tenant_id, codigo).
    """

    __tablename__ = "carrera"
    __table_args__ = (UniqueConstraint("tenant_id", "codigo", name="uq_carrera_tenant_codigo"),)

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")


class Cohorte(TenantScopedMixin, Base):
    """Cohorte (camada / ingreso) dentro de una Carrera.

    Unicidad: (tenant_id, carrera_id, nombre).
    vig_hasta nulo = vigencia abierta.
    """

    __tablename__ = "cohorte"
    __table_args__ = (UniqueConstraint("tenant_id", "carrera_id", "nombre", name="uq_cohorte_tenant_carrera_nombre"),)

    carrera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    vig_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vig_hasta: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")


class Materia(TenantScopedMixin, Base):
    """Unidad del catálogo académico del tenant.

    Catálogo único por tenant (ADR-006). Unicidad: (tenant_id, codigo).
    """

    __tablename__ = "materia"
    __table_args__ = (UniqueConstraint("tenant_id", "codigo", name="uq_materia_tenant_codigo"),)

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")
