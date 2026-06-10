"""audit log — append-only table with immutability trigger

Revision ID: 004_audit_log
Revises: 003_rbac
Create Date: 2026-06-08 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_audit_log"
down_revision = "003_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create audit_log table
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impersonado_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(length=100), nullable=False),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("filas_afectadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["impersonado_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # 2. Indexes for common query patterns
    # ------------------------------------------------------------------
    op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_log_fecha_hora"), "audit_log", ["fecha_hora"], unique=False)
    op.create_index(op.f("ix_audit_log_accion"), "audit_log", ["accion"], unique=False)

    # ------------------------------------------------------------------
    # 3. Append-only trigger — rejects any UPDATE or DELETE at DB level
    # Design decision D1: two-level enforcement (app + DB).
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_immutable_fn()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable_fn();
        """
    )


def downgrade() -> None:
    # Drop trigger and function first, then table + indexes
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_immutable_fn")

    op.drop_index(op.f("ix_audit_log_accion"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_fecha_hora"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_tenant_id"), table_name="audit_log")

    op.drop_table("audit_log")
