"""estructura academica carrera cohorte materia

Revision ID: 004_estructura_academica
Revises: 004_audit_log
Create Date: 2026-06-10 00:00:00

Nota: el permiso 'estructura:gestionar' ya fue sembrado en 003_rbac
dentro de ALL_PERMISSIONS y asignado al rol ADMIN. No se re-siembra
aquí para evitar duplicación de lógica; el seed de 003 es idempotente.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_estructura_academica"
down_revision = "004_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Tabla carrera
    # ------------------------------------------------------------------
    op.create_table(
        "carrera",
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_carrera_tenant_codigo"),
    )
    op.create_index(op.f("ix_carrera_tenant_id"), "carrera", ["tenant_id"], unique=False)

    # ------------------------------------------------------------------
    # 2. Tabla cohorte
    # ------------------------------------------------------------------
    op.create_table(
        "cohorte",
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("vig_desde", sa.Date(), nullable=False),
        sa.Column("vig_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["carrera_id"], ["carrera.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "carrera_id", "nombre", name="uq_cohorte_tenant_carrera_nombre"),
    )
    op.create_index(op.f("ix_cohorte_carrera_id"), "cohorte", ["carrera_id"], unique=False)
    op.create_index(op.f("ix_cohorte_tenant_id"), "cohorte", ["tenant_id"], unique=False)

    # ------------------------------------------------------------------
    # 3. Tabla materia
    # ------------------------------------------------------------------
    op.create_table(
        "materia",
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_materia_tenant_codigo"),
    )
    op.create_index(op.f("ix_materia_tenant_id"), "materia", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_materia_tenant_id"), table_name="materia")
    op.drop_table("materia")

    op.drop_index(op.f("ix_cohorte_tenant_id"), table_name="cohorte")
    op.drop_index(op.f("ix_cohorte_carrera_id"), table_name="cohorte")
    op.drop_table("cohorte")

    op.drop_index(op.f("ix_carrera_tenant_id"), table_name="carrera")
    op.drop_table("carrera")
