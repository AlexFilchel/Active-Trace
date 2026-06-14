"""encuentros y guardias

Revision ID: 010_encuentros_guardias
Revises: 009_comunicaciones
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "010_encuentros_guardias"
down_revision = "009_comunicaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slot_encuentro",
        sa.Column("asignacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("hora", sa.Time(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("cant_semanas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fecha_unica", sa.Date(), nullable=True),
        sa.Column("meet_url", sa.String(length=500), nullable=True),
        sa.Column("vig_desde", sa.Date(), nullable=True),
        sa.Column("vig_hasta", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asignacion_id"], ["asignacion.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_slot_encuentro_tenant_id", "slot_encuentro", ["tenant_id"], unique=False)
    op.create_index("ix_slot_encuentro_materia_id", "slot_encuentro", ["materia_id"], unique=False)
    op.create_index("ix_slot_encuentro_asignacion_id", "slot_encuentro", ["asignacion_id"], unique=False)

    op.create_table(
        "instancia_encuentro",
        sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("hora", sa.Time(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Programado"),
        sa.Column("meet_url", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["slot_id"], ["slot_encuentro.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_instancia_encuentro_tenant_id", "instancia_encuentro", ["tenant_id"], unique=False)
    op.create_index("ix_instancia_encuentro_materia_id", "instancia_encuentro", ["materia_id"], unique=False)
    op.create_index("ix_instancia_encuentro_slot_id", "instancia_encuentro", ["slot_id"], unique=False)

    op.create_table(
        "guardia",
        sa.Column("asignacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("horario", sa.String(length=50), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Pendiente"),
        sa.Column("comentarios", sa.Text(), nullable=True),
        sa.Column("creada_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asignacion_id"], ["asignacion.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carrera.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guardia_tenant_id", "guardia", ["tenant_id"], unique=False)
    op.create_index("ix_guardia_materia_id", "guardia", ["materia_id"], unique=False)
    op.create_index("ix_guardia_asignacion_id", "guardia", ["asignacion_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_guardia_asignacion_id", table_name="guardia")
    op.drop_index("ix_guardia_materia_id", table_name="guardia")
    op.drop_index("ix_guardia_tenant_id", table_name="guardia")
    op.drop_table("guardia")

    op.drop_index("ix_instancia_encuentro_slot_id", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_materia_id", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_tenant_id", table_name="instancia_encuentro")
    op.drop_table("instancia_encuentro")

    op.drop_index("ix_slot_encuentro_asignacion_id", table_name="slot_encuentro")
    op.drop_index("ix_slot_encuentro_materia_id", table_name="slot_encuentro")
    op.drop_index("ix_slot_encuentro_tenant_id", table_name="slot_encuentro")
    op.drop_table("slot_encuentro")
