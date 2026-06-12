"""usuarios y asignaciones

Revision ID: 005_usuarios_asignaciones
Revises: 004_estructura_academica
Create Date: 2026-06-11 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_usuarios_asignaciones"
down_revision = "004_estructura_academica"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_permission(bind, *, tenant_id: str, permission_name: str) -> str:
    now = _utc_now()
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
    return str(
        bind.execute(
            sa.text("SELECT id FROM permiso WHERE tenant_id = :tenant_id AND nombre = :nombre"),
            {"tenant_id": tenant_id, "nombre": permission_name},
        ).scalar_one()
    )


def _seed_role_permission(bind, *, tenant_id: str, role_name: str, permission_id: str) -> None:
    role_id = bind.execute(
        sa.text("SELECT id FROM rol WHERE tenant_id = :tenant_id AND nombre = :nombre"),
        {"tenant_id": tenant_id, "nombre": role_name},
    ).scalar_one_or_none()
    if role_id is None:
        return

    now = _utc_now()
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
            "permiso_id": permission_id,
            "created_at": now,
            "updated_at": now,
        },
    )


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("auth_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("apellidos", sa.String(length=120), nullable=False),
        sa.Column("email_encrypted", sa.String(length=512), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("dni_encrypted", sa.String(length=512), nullable=True),
        sa.Column("cuil_encrypted", sa.String(length=512), nullable=True),
        sa.Column("cbu_encrypted", sa.String(length=512), nullable=True),
        sa.Column("alias_cbu_encrypted", sa.String(length=512), nullable=True),
        sa.Column("banco", sa.String(length=120), nullable=True),
        sa.Column("regional", sa.String(length=120), nullable=True),
        sa.Column("legajo", sa.String(length=120), nullable=True),
        sa.Column("legajo_profesional", sa.String(length=120), nullable=True),
        sa.Column("facturador", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activo"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["auth_user_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "auth_user_id", name="uq_usuario_tenant_auth_user"),
        sa.UniqueConstraint("tenant_id", "email_hash", name="uq_usuario_tenant_email_hash"),
    )
    op.create_index(op.f("ix_usuario_auth_user_id"), "usuario", ["auth_user_id"], unique=False)
    op.create_index(op.f("ix_usuario_email_hash"), "usuario", ["email_hash"], unique=False)
    op.create_index(op.f("ix_usuario_tenant_id"), "usuario", ["tenant_id"], unique=False)
    op.create_index(
        "uq_usuario_tenant_legajo_present",
        "usuario",
        ["tenant_id", "legajo"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND legajo IS NOT NULL"),
    )

    op.create_table(
        "asignacion",
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("responsable_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comisiones", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("desde", sa.Date(), nullable=False),
        sa.Column("hasta", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_asignacion_hasta_desde"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carrera.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsable_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asignacion_usuario_id"), "asignacion", ["usuario_id"], unique=False)
    op.create_index(op.f("ix_asignacion_rol_id"), "asignacion", ["rol_id"], unique=False)
    op.create_index(op.f("ix_asignacion_materia_id"), "asignacion", ["materia_id"], unique=False)
    op.create_index(op.f("ix_asignacion_carrera_id"), "asignacion", ["carrera_id"], unique=False)
    op.create_index(op.f("ix_asignacion_cohorte_id"), "asignacion", ["cohorte_id"], unique=False)
    op.create_index(op.f("ix_asignacion_responsable_id"), "asignacion", ["responsable_id"], unique=False)
    op.create_index(op.f("ix_asignacion_desde"), "asignacion", ["desde"], unique=False)
    op.create_index(op.f("ix_asignacion_hasta"), "asignacion", ["hasta"], unique=False)
    op.create_index(op.f("ix_asignacion_tenant_id"), "asignacion", ["tenant_id"], unique=False)

    bind = op.get_bind()
    tenant_ids = [str(row[0]) for row in bind.execute(sa.text("SELECT id FROM tenant")).fetchall()]
    for tenant_id in tenant_ids:
        usuarios_permission_id = _seed_permission(bind, tenant_id=tenant_id, permission_name="usuarios:gestionar")
        equipos_permission_id = _seed_permission(bind, tenant_id=tenant_id, permission_name="equipos:asignar")
        _seed_role_permission(bind, tenant_id=tenant_id, role_name="ADMIN", permission_id=usuarios_permission_id)
        _seed_role_permission(bind, tenant_id=tenant_id, role_name="ADMIN", permission_id=equipos_permission_id)
        _seed_role_permission(bind, tenant_id=tenant_id, role_name="COORDINADOR", permission_id=equipos_permission_id)


def downgrade() -> None:
    bind = op.get_bind()
    for permission_name in ("usuarios:gestionar", "equipos:asignar"):
        bind.execute(
            sa.text(
                "DELETE FROM rol_permiso WHERE permiso_id IN ("
                "SELECT id FROM permiso WHERE nombre = :permission_name"
                ")"
            ),
            {"permission_name": permission_name},
        )
        bind.execute(
            sa.text("DELETE FROM permiso WHERE nombre = :permission_name"),
            {"permission_name": permission_name},
        )

    op.drop_index(op.f("ix_asignacion_tenant_id"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_hasta"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_desde"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_responsable_id"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_cohorte_id"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_carrera_id"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_materia_id"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_rol_id"), table_name="asignacion")
    op.drop_index(op.f("ix_asignacion_usuario_id"), table_name="asignacion")
    op.drop_table("asignacion")

    op.drop_index("uq_usuario_tenant_legajo_present", table_name="usuario")
    op.drop_index(op.f("ix_usuario_tenant_id"), table_name="usuario")
    op.drop_index(op.f("ix_usuario_email_hash"), table_name="usuario")
    op.drop_index(op.f("ix_usuario_auth_user_id"), table_name="usuario")
    op.drop_table("usuario")
