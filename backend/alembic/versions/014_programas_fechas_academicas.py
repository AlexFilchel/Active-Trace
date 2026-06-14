"""programas y fechas academicas

Revision ID: 014_programas_fechas_academicas
Revises: 013_tareas_internas
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "014_programas_fechas_academicas"
down_revision = "013_tareas_internas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- programa_materia ---
    op.create_table(
        "programa_materia",
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("referencia_archivo", sa.Text, nullable=False),
        sa.Column("cargado_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carrera.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_programa_materia_tenant_id", "programa_materia", ["tenant_id"], unique=False)
    op.create_index("ix_programa_materia_materia_id", "programa_materia", ["materia_id"], unique=False)
    op.create_index("ix_programa_materia_carrera_id", "programa_materia", ["carrera_id"], unique=False)
    op.create_index("ix_programa_materia_cohorte_id", "programa_materia", ["cohorte_id"], unique=False)

    # --- fecha_academica ---
    op.create_table(
        "fecha_academica",
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("periodo", sa.String(length=20), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fecha_academica_tenant_id", "fecha_academica", ["tenant_id"], unique=False)
    op.create_index("ix_fecha_academica_materia_id", "fecha_academica", ["materia_id"], unique=False)
    op.create_index("ix_fecha_academica_cohorte_id", "fecha_academica", ["cohorte_id"], unique=False)
    op.create_index("ix_fecha_academica_tipo", "fecha_academica", ["tipo"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fecha_academica_tipo", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_cohorte_id", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_materia_id", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_tenant_id", table_name="fecha_academica")
    op.drop_table("fecha_academica")

    op.drop_index("ix_programa_materia_cohorte_id", table_name="programa_materia")
    op.drop_index("ix_programa_materia_carrera_id", table_name="programa_materia")
    op.drop_index("ix_programa_materia_materia_id", table_name="programa_materia")
    op.drop_index("ix_programa_materia_tenant_id", table_name="programa_materia")
    op.drop_table("programa_materia")
