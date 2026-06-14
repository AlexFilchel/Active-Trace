"""auditoria permiso seed

Revision ID: 015_auditoria_permiso
Revises: 014_programas_fechas_academicas
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "015_auditoria_permiso"
down_revision = "014_programas_fechas_academicas"
branch_labels = None
depends_on = None

_PERMISO = "auditoria:ver"
_ROLES = ("ADMIN", "COORDINADOR", "FINANZAS")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()
    tenant_rows = bind.execute(sa.text("SELECT id FROM tenant")).fetchall()
    now = _utc_now()

    for (tenant_id_raw,) in tenant_rows:
        tenant_id = str(tenant_id_raw)

        bind.execute(
            sa.text(
                "INSERT INTO permiso (id, tenant_id, nombre, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :nombre, :created_at, :updated_at) "
                "ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "nombre": _PERMISO,
                "created_at": now,
                "updated_at": now,
            },
        )

        permiso_row = bind.execute(
            sa.text("SELECT id FROM permiso WHERE tenant_id = :tid AND nombre = :nombre"),
            {"tid": tenant_id, "nombre": _PERMISO},
        ).fetchone()
        if permiso_row is None:
            continue
        permiso_id = str(permiso_row[0])

        role_rows = bind.execute(
            sa.text(
                "SELECT id FROM rol WHERE tenant_id = :tid AND nombre = ANY(:roles)"
            ),
            {"tid": tenant_id, "roles": list(_ROLES)},
        ).fetchall()

        for (role_id_raw,) in role_rows:
            bind.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :rol_id, :permiso_id, :created_at, :updated_at) "
                    "ON CONFLICT ON CONSTRAINT uq_rol_permiso_rol_permiso DO NOTHING"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "rol_id": str(role_id_raw),
                    "permiso_id": permiso_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    # No-op: removing the permission would not break anything,
    # but leaving it is safer for rollback scenarios.
    pass
