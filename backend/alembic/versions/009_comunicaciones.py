"""comunicaciones cola worker

Revision ID: 009_comunicaciones
Revises: 008_finalizacion_actividad
Create Date: 2026-06-13 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "009_comunicaciones"
down_revision = "008_finalizacion_actividad"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    op.add_column("tenant", sa.Column("comunicaciones_aprobacion_requerida", sa.Boolean(), nullable=True))
    op.add_column("tenant", sa.Column("comunicaciones_aprobacion_masiva", sa.Boolean(), nullable=True))

    op.create_table(
        "comunicacion",
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entrada_padron_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enviado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destinatario_encrypted", sa.String(length=512), nullable=False),
        sa.Column("asunto", sa.String(length=255), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("requiere_aprobacion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("aprobado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprobado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("enviado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detalle", sa.String(length=255), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["aprobado_por"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelado_por"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["entrada_padron_id"], ["entrada_padron.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["enviado_por"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comunicacion_tenant_id", "comunicacion", ["tenant_id"], unique=False)
    op.create_index("ix_comunicacion_tenant_estado", "comunicacion", ["tenant_id", "estado"], unique=False)
    op.create_index("ix_comunicacion_tenant_lote", "comunicacion", ["tenant_id", "lote_id"], unique=False)
    op.create_index("ix_comunicacion_tenant_materia", "comunicacion", ["tenant_id", "materia_id"], unique=False)
    op.create_index("ix_comunicacion_tenant_idempotency", "comunicacion", ["tenant_id", "idempotency_key"], unique=False)

    bind = op.get_bind()
    tenant_rows = bind.execute(sa.text("SELECT id FROM tenant")).fetchall()
    now = _utc_now()

    for tenant_row in tenant_rows:
        tenant_id = str(tenant_row[0])
        for permission_name in ("comunicacion:enviar", "comunicacion:aprobar"):
            bind.execute(
                sa.text(
                    "INSERT INTO permiso (id, tenant_id, nombre, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :nombre, :created_at, :updated_at) "
                    "ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "nombre": permission_name,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        role_rows = bind.execute(
            sa.text("SELECT id, nombre FROM rol WHERE tenant_id = :tenant_id AND nombre IN ('COORDINADOR', 'ADMIN')"),
            {"tenant_id": tenant_id},
        ).fetchall()
        for role_id, _role_name in role_rows:
            for permission_name in ("comunicacion:enviar", "comunicacion:aprobar"):
                permiso_row = bind.execute(
                    sa.text("SELECT id FROM permiso WHERE tenant_id = :tenant_id AND nombre = :nombre"),
                    {"tenant_id": tenant_id, "nombre": permission_name},
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
    op.drop_index("ix_comunicacion_tenant_idempotency", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_materia", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_lote", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_estado", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_id", table_name="comunicacion")
    op.drop_table("comunicacion")
    op.drop_column("tenant", "comunicaciones_aprobacion_masiva")
    op.drop_column("tenant", "comunicaciones_aprobacion_requerida")
