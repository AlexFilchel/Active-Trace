"""tareas internas

Revision ID: 013_tareas_internas
Revises: 012_avisos_acknowledgment
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013_tareas_internas"
down_revision = "012_avisos_acknowledgment"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # --- tarea ---
    op.create_table(
        "tarea",
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asignado_a", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asignado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Pendiente"),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("contexto_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asignado_a"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tarea_tenant_id", "tarea", ["tenant_id"], unique=False)
    op.create_index("ix_tarea_asignado_a", "tarea", ["asignado_a"], unique=False)
    op.create_index("ix_tarea_asignado_por", "tarea", ["asignado_por"], unique=False)
    op.create_index("ix_tarea_materia_id", "tarea", ["materia_id"], unique=False)
    op.create_index("ix_tarea_estado", "tarea", ["estado"], unique=False)

    # --- comentario_tarea ---
    op.create_table(
        "comentario_tarea",
        sa.Column("tarea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("autor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column("comentado_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tarea_id"], ["tarea.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comentario_tarea_tenant_id", "comentario_tarea", ["tenant_id"], unique=False)
    op.create_index("ix_comentario_tarea_tarea_id", "comentario_tarea", ["tarea_id"], unique=False)

    # --- Seed: permiso tareas:gestionar para COORDINADOR, ADMIN, PROFESOR, TUTOR ---
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
                "nombre": "tareas:gestionar",
                "created_at": now,
                "updated_at": now,
            },
        )
        role_rows = bind.execute(
            sa.text(
                "SELECT id FROM rol WHERE tenant_id = :tenant_id "
                "AND nombre IN ('COORDINADOR', 'ADMIN', 'PROFESOR', 'TUTOR')"
            ),
            {"tenant_id": tenant_id},
        ).fetchall()
        for (role_id,) in role_rows:
            permiso_row = bind.execute(
                sa.text("SELECT id FROM permiso WHERE tenant_id = :tenant_id AND nombre = :nombre"),
                {"tenant_id": tenant_id, "nombre": "tareas:gestionar"},
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
            "(SELECT id FROM permiso WHERE nombre = 'tareas:gestionar')"
        )
    )
    bind.execute(sa.text("DELETE FROM permiso WHERE nombre = 'tareas:gestionar'"))

    op.drop_index("ix_comentario_tarea_tarea_id", table_name="comentario_tarea")
    op.drop_index("ix_comentario_tarea_tenant_id", table_name="comentario_tarea")
    op.drop_table("comentario_tarea")

    op.drop_index("ix_tarea_estado", table_name="tarea")
    op.drop_index("ix_tarea_materia_id", table_name="tarea")
    op.drop_index("ix_tarea_asignado_por", table_name="tarea")
    op.drop_index("ix_tarea_asignado_a", table_name="tarea")
    op.drop_index("ix_tarea_tenant_id", table_name="tarea")
    op.drop_table("tarea")
