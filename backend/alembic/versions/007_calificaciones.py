"""calificaciones y umbral_materia

Revision ID: 007_calificaciones
Revises: 006_padron
Create Date: 2026-06-12 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "007_calificaciones"
down_revision = "006_padron"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calificacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entrada_padron_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entrada_padron.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actividad", sa.String(300), nullable=False),
        sa.Column("nota_numerica", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("nota_textual", sa.String(100), nullable=True),
        sa.Column("aprobado", sa.Boolean, nullable=False),
        sa.Column("origen", sa.String(50), nullable=False, server_default="Importado"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_calificacion_tenant_id", "calificacion", ["tenant_id"])
    op.create_index("ix_calificacion_entrada_padron_id", "calificacion", ["entrada_padron_id"])
    op.create_index("ix_calificacion_actor_id", "calificacion", ["actor_id"])
    op.create_unique_constraint(
        "uq_calificacion_entrada_actividad_actor",
        "calificacion",
        ["tenant_id", "entrada_padron_id", "actividad", "actor_id"],
    )

    op.create_table(
        "umbral_materia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asignacion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asignacion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("umbral_pct", sa.Numeric(precision=5, scale=2), nullable=False, server_default="60"),
        sa.Column("valores_aprobatorios", postgresql.ARRAY(sa.String), nullable=False, server_default=sa.text("ARRAY['Satisfactorio','Supera lo esperado']")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_umbral_materia_tenant_id", "umbral_materia", ["tenant_id"])
    op.create_unique_constraint(
        "uq_umbral_materia_asignacion",
        "umbral_materia",
        ["tenant_id", "asignacion_id", "materia_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_umbral_materia_asignacion", "umbral_materia", type_="unique")
    op.drop_index("ix_umbral_materia_tenant_id", "umbral_materia")
    op.drop_table("umbral_materia")

    op.drop_constraint("uq_calificacion_entrada_actividad_actor", "calificacion", type_="unique")
    op.drop_index("ix_calificacion_actor_id", "calificacion")
    op.drop_index("ix_calificacion_entrada_padron_id", "calificacion")
    op.drop_index("ix_calificacion_tenant_id", "calificacion")
    op.drop_table("calificacion")
