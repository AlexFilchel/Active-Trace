"""mensajería interna — hilo_mensaje y mensaje_interno

Revision ID: 017_mensajeria_interna
Revises: 016_liquidaciones_honorarios
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "017_mensajeria_interna"
down_revision = "016_liquidaciones_honorarios"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    op.create_table(
        "hilo_mensaje",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("asunto", sa.String(200), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, default=_utc_now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, default=_utc_now),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hilo_mensaje_creado_por", "hilo_mensaje", ["creado_por"])

    op.create_table(
        "mensaje_interno",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("hilo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hilo_mensaje.id", ondelete="CASCADE"), nullable=False),
        sa.Column("remitente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destinatario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cuerpo", sa.Text, nullable=False),
        sa.Column("leido", sa.Boolean, nullable=False, default=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, default=_utc_now),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, default=_utc_now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, default=_utc_now),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mensaje_interno_hilo_id", "mensaje_interno", ["hilo_id"])
    op.create_index(
        "ix_mensaje_interno_destinatario_leido",
        "mensaje_interno",
        ["tenant_id", "destinatario_id", "leido"],
    )


def downgrade() -> None:
    op.drop_table("mensaje_interno")
    op.drop_table("hilo_mensaje")
