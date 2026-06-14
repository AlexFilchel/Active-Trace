"""avisos y acknowledgment

Revision ID: 012_avisos_acknowledgment
Revises: 011_evaluaciones_coloquios
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012_avisos_acknowledgment"
down_revision = "011_evaluaciones_coloquios"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # --- aviso ---
    op.create_table(
        "aviso",
        sa.Column("alcance", sa.String(length=20), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rol_destino", sa.String(length=50), nullable=True),
        sa.Column("severidad", sa.String(length=20), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("cuerpo", sa.Text, nullable=False),
        sa.Column("inicio_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requiere_ack", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aviso_tenant_id", "aviso", ["tenant_id"], unique=False)
    op.create_index("ix_aviso_materia_id", "aviso", ["materia_id"], unique=False)
    op.create_index("ix_aviso_cohorte_id", "aviso", ["cohorte_id"], unique=False)
    op.create_index("ix_aviso_inicio_en", "aviso", ["inicio_en"], unique=False)

    # --- acknowledgment_aviso ---
    op.create_table(
        "acknowledgment_aviso",
        sa.Column("aviso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmado_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["aviso_id"], ["aviso.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "aviso_id", "usuario_id", name="uq_ack_aviso_tenant_aviso_usuario"),
    )
    op.create_index("ix_ack_aviso_tenant_id", "acknowledgment_aviso", ["tenant_id"], unique=False)
    op.create_index("ix_ack_aviso_aviso_id", "acknowledgment_aviso", ["aviso_id"], unique=False)
    op.create_index("ix_ack_aviso_usuario_id", "acknowledgment_aviso", ["usuario_id"], unique=False)

    # --- Seed: permiso avisos:publicar para COORDINADOR y ADMIN ---
    bind = op.get_bind()
    tenant_rows = bind.execute(sa.text("SELECT id FROM tenant")).fetchall()
    now = _utc_now()

    for tenant_row in tenant_rows:
        tenant_id = str(tenant_row[0])
        bind.execute(
            sa.text(
                "INSERT INTO permiso (id, tenant_id, nombre, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :nombre, :created_at, :updated_at) "
                "ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "nombre": "avisos:publicar",
                "created_at": now,
                "updated_at": now,
            },
        )
        role_rows = bind.execute(
            sa.text(
                "SELECT id FROM rol WHERE tenant_id = :tenant_id AND nombre IN ('COORDINADOR', 'ADMIN')"
            ),
            {"tenant_id": tenant_id},
        ).fetchall()
        for (role_id,) in role_rows:
            permiso_row = bind.execute(
                sa.text("SELECT id FROM permiso WHERE tenant_id = :tenant_id AND nombre = :nombre"),
                {"tenant_id": tenant_id, "nombre": "avisos:publicar"},
            ).fetchone()
            if permiso_row is None:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :rol_id, :permiso_id, :created_at, :updated_at) "
                    "ON CONFLICT ON CONSTRAINT uq_rol_permiso_rol_permiso DO NOTHING"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "rol_id": str(role_id),
                    "permiso_id": str(permiso_row[0]),
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM rol_permiso WHERE permiso_id IN "
            "(SELECT id FROM permiso WHERE nombre = 'avisos:publicar')"
        )
    )
    bind.execute(sa.text("DELETE FROM permiso WHERE nombre = 'avisos:publicar'"))

    op.drop_index("ix_ack_aviso_usuario_id", table_name="acknowledgment_aviso")
    op.drop_index("ix_ack_aviso_aviso_id", table_name="acknowledgment_aviso")
    op.drop_index("ix_ack_aviso_tenant_id", table_name="acknowledgment_aviso")
    op.drop_table("acknowledgment_aviso")

    op.drop_index("ix_aviso_inicio_en", table_name="aviso")
    op.drop_index("ix_aviso_cohorte_id", table_name="aviso")
    op.drop_index("ix_aviso_materia_id", table_name="aviso")
    op.drop_index("ix_aviso_tenant_id", table_name="aviso")
    op.drop_table("aviso")
