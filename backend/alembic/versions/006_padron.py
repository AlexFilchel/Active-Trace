"""padron versionado — VersionPadron y EntradaPadron

Revision ID: 006_padron
Revises: 005_usuarios_asignaciones
Create Date: 2026-06-12 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006_padron"
down_revision = "005_usuarios_asignaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "version_padron",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cargado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cargado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("activa", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial unique index: only one active version per (tenant, materia, cohorte)
    op.create_index(
        "uq_version_padron_activa",
        "version_padron",
        ["tenant_id", "materia_id", "cohorte_id"],
        unique=True,
        postgresql_where=sa.text("activa = true"),
    )
    op.create_index("ix_version_padron_tenant_id", "version_padron", ["tenant_id"])
    op.create_index("ix_version_padron_materia_id", "version_padron", ["materia_id"])

    op.create_table(
        "entrada_padron",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("version_padron.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("apellidos", sa.String(200), nullable=False),
        sa.Column("email_encrypted", sa.String(512), nullable=False),
        sa.Column("email_hash", sa.String(128), nullable=False),
        sa.Column("comision", sa.String(200), nullable=True),
        sa.Column("regional", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_entrada_padron_version_id", "entrada_padron", ["version_id"])
    op.create_index("ix_entrada_padron_tenant_id", "entrada_padron", ["tenant_id"])
    op.create_index("ix_entrada_padron_email_hash", "entrada_padron", ["email_hash"])

    # Add Moodle WS config columns to tenant
    op.add_column("tenant", sa.Column("moodle_ws_url", sa.String(500), nullable=True))
    op.add_column("tenant", sa.Column("moodle_ws_token_encrypted", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant", "moodle_ws_token_encrypted")
    op.drop_column("tenant", "moodle_ws_url")

    op.drop_index("ix_entrada_padron_email_hash", "entrada_padron")
    op.drop_index("ix_entrada_padron_tenant_id", "entrada_padron")
    op.drop_index("ix_entrada_padron_version_id", "entrada_padron")
    op.drop_table("entrada_padron")

    op.drop_index("ix_version_padron_materia_id", "version_padron")
    op.drop_index("ix_version_padron_tenant_id", "version_padron")
    op.drop_index("uq_version_padron_activa", "version_padron")
    op.drop_table("version_padron")
