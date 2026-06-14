from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin


class Comunicacion(TenantScopedMixin, Base):
    __tablename__ = "comunicacion"
    __table_args__ = (
        Index("ix_comunicacion_tenant_estado", "tenant_id", "estado"),
        Index("ix_comunicacion_tenant_lote", "tenant_id", "lote_id"),
        Index("ix_comunicacion_tenant_materia", "tenant_id", "materia_id"),
        Index("ix_comunicacion_tenant_idempotency", "tenant_id", "idempotency_key"),
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False)
    entrada_padron_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entrada_padron.id", ondelete="RESTRICT"), nullable=False)
    enviado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth_user.id", ondelete="RESTRICT"), nullable=False)
    destinatario_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    asunto: Mapped[str] = mapped_column(String(255), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Pendiente")
    lote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    requiere_aprobacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aprobado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    aprobado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("auth_user.id", ondelete="RESTRICT"), nullable=True, default=None)
    cancelado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    cancelado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("auth_user.id", ondelete="RESTRICT"), nullable=True, default=None)
    enviado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    error_detalle: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
