"""finalizacion_actividad

Revision ID: 008_finalizacion_actividad
Revises: 007_calificaciones
Create Date: 2026-06-13 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "008_finalizacion_actividad"
down_revision = "007_calificaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finalizacion_actividad",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entrada_padron_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entrada_padron.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actividad", sa.String(300), nullable=False),
        sa.Column("es_textual", sa.Boolean(), nullable=False),
        sa.Column("finalizado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_finalizacion_actividad_tenant_id", "finalizacion_actividad", ["tenant_id"])
    op.create_index("ix_finalizacion_actividad_entrada_padron_id", "finalizacion_actividad", ["entrada_padron_id"])
    op.create_unique_constraint(
        "uq_finalizacion_actividad_entrada",
        "finalizacion_actividad",
        ["tenant_id", "entrada_padron_id", "actividad"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_finalizacion_actividad_entrada", "finalizacion_actividad", type_="unique")
    op.drop_index("ix_finalizacion_actividad_entrada_padron_id", "finalizacion_actividad")
    op.drop_index("ix_finalizacion_actividad_tenant_id", "finalizacion_actividad")
    op.drop_table("finalizacion_actividad")
