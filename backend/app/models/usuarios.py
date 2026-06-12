from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class Usuario(TenantScopedMixin, Base):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("tenant_id", "auth_user_id", name="uq_usuario_tenant_auth_user"),
        UniqueConstraint("tenant_id", "email_hash", name="uq_usuario_tenant_email_hash"),
        Index(
            "uq_usuario_tenant_legajo_present",
            "tenant_id",
            "legajo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND legajo IS NOT NULL"),
        ),
    )

    auth_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_user.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(120), nullable=False)
    email_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dni_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    cuil_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    cbu_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    alias_cbu_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    banco: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    regional: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    legajo: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    legajo_profesional: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    facturador: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activo")


class Asignacion(TenantScopedMixin, Base):
    __tablename__ = "asignacion"
    __table_args__ = (CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_asignacion_hasta_desde"),)

    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False, index=True)
    rol_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rol.id", ondelete="RESTRICT"), nullable=False, index=True)
    materia_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materia.id", ondelete="RESTRICT"), nullable=True, default=None, index=True)
    carrera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("carrera.id", ondelete="RESTRICT"), nullable=True, default=None, index=True)
    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=True, default=None, index=True)
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=True, default=None, index=True)
    comisiones: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    desde: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True, default=None, index=True)

    @property
    def estado_vigencia(self) -> str:
        today = date.today()
        if self.desde > today:
            return "Futura"
        if self.hasta is not None and self.hasta < today:
            return "Vencida"
        return "Vigente"
