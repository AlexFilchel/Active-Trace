"""RBAC models: Rol, Permiso, RolPermiso.

Tablas de catálogo administrables por tenant. Nombres de permisos en formato
modulo:accion (ej. calificaciones:importar). Unicidades enforceadas a nivel DB.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class Rol(TenantScopedMixin, Base):
    """Catálogo de roles por tenant.

    Unicidad: (tenant_id, nombre).
    """

    __tablename__ = "rol"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre", name="uq_rol_tenant_nombre"),)

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)


class Permiso(TenantScopedMixin, Base):
    """Catálogo de permisos por tenant en formato modulo:accion.

    Unicidad: (tenant_id, nombre).
    """

    __tablename__ = "permiso"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre", name="uq_permiso_tenant_nombre"),)

    nombre: Mapped[str] = mapped_column(String(64), nullable=False)


class RolPermiso(TenantScopedMixin, Base):
    """Asociación Rol × Permiso dentro de un tenant.

    Unicidad: (rol_id, permiso_id).
    """

    __tablename__ = "rol_permiso"
    __table_args__ = (UniqueConstraint("rol_id", "permiso_id", name="uq_rol_permiso_rol_permiso"),)

    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rol.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permiso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permiso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
