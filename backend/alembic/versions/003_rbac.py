"""rbac roles permisos

Revision ID: 003_rbac
Revises: 002_auth_jwt_2fa
Create Date: 2026-06-08 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003_rbac"
down_revision = "002_auth_jwt_2fa"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Dominio: roles y permisos base (según 03_actores_y_roles.md §3.3)
# ---------------------------------------------------------------------------

DOMAIN_ROLES: list[tuple[str, str]] = [
    ("ALUMNO", "Estudiante que cursa materias"),
    ("TUTOR", "Auxiliar / ayudante de cátedra"),
    ("PROFESOR", "Docente a cargo de una o más comisiones"),
    ("COORDINADOR", "Responsable de un conjunto de materias o cohorte"),
    ("NEXO", "Rol de articulación / enlace transversal"),
    ("ADMIN", "Administrador del sistema dentro del tenant"),
    ("FINANZAS", "Responsable de liquidaciones y honorarios"),
]

# Permisos del catálogo base — formato modulo:accion
ALL_PERMISSIONS: list[str] = [
    "estado_academico:ver_propio",
    "evaluacion:reservar_instancia",
    "avisos:confirmar",
    "calificaciones:importar",
    "atrasados:ver",
    "entregas:ver_sin_corregir",
    "comunicacion:enviar",
    "comunicacion:aprobar_masiva",
    "encuentros:gestionar",
    "guardias:registrar",
    "tareas:gestionar",
    "avisos:publicar",
    "equipos:gestionar",
    "estructura:gestionar",
    "usuarios:gestionar",
    "auditoria:ver",
    "liquidaciones:operar_grilla",
    "liquidaciones:cerrar",
    "facturas:gestionar",
    "tenant:configurar",
    "impersonacion:usar",
]

# Matriz rol → permisos (lista de permisos que tiene cada rol)
ROL_PERMISOS: dict[str, list[str]] = {
    "ALUMNO": [
        "estado_academico:ver_propio",
        "evaluacion:reservar_instancia",
        "avisos:confirmar",
    ],
    "TUTOR": [
        "avisos:confirmar",
        "atrasados:ver",
        "entregas:ver_sin_corregir",
        "encuentros:gestionar",
        "guardias:registrar",
    ],
    "PROFESOR": [
        "avisos:confirmar",
        "calificaciones:importar",
        "atrasados:ver",
        "entregas:ver_sin_corregir",
        "comunicacion:enviar",
        "encuentros:gestionar",
        "guardias:registrar",
        "tareas:gestionar",
    ],
    "COORDINADOR": [
        "avisos:confirmar",
        "calificaciones:importar",
        "atrasados:ver",
        "entregas:ver_sin_corregir",
        "comunicacion:enviar",
        "comunicacion:aprobar_masiva",
        "encuentros:gestionar",
        "guardias:registrar",
        "tareas:gestionar",
        "avisos:publicar",
        "equipos:gestionar",
        "auditoria:ver",
    ],
    "NEXO": [
        "avisos:confirmar",
        "comunicacion:enviar",
        "encuentros:gestionar",
    ],
    "ADMIN": [
        "avisos:confirmar",
        "calificaciones:importar",
        "atrasados:ver",
        "entregas:ver_sin_corregir",
        "comunicacion:enviar",
        "comunicacion:aprobar_masiva",
        "encuentros:gestionar",
        "guardias:registrar",
        "tareas:gestionar",
        "avisos:publicar",
        "equipos:gestionar",
        "estructura:gestionar",
        "usuarios:gestionar",
        "auditoria:ver",
        "tenant:configurar",
        "impersonacion:usar",
    ],
    "FINANZAS": [
        "avisos:confirmar",
        "auditoria:ver",
        "liquidaciones:operar_grilla",
        "liquidaciones:cerrar",
        "facturas:gestionar",
    ],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Crear tabla rol
    # ------------------------------------------------------------------
    op.create_table(
        "rol",
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nombre", name="uq_rol_tenant_nombre"),
    )
    op.create_index(op.f("ix_rol_tenant_id"), "rol", ["tenant_id"], unique=False)

    # ------------------------------------------------------------------
    # 2. Crear tabla permiso
    # ------------------------------------------------------------------
    op.create_table(
        "permiso",
        sa.Column("nombre", sa.String(length=64), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nombre", name="uq_permiso_tenant_nombre"),
    )
    op.create_index(op.f("ix_permiso_tenant_id"), "permiso", ["tenant_id"], unique=False)

    # ------------------------------------------------------------------
    # 3. Crear tabla rol_permiso
    # ------------------------------------------------------------------
    op.create_table(
        "rol_permiso",
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permiso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["permiso_id"], ["permiso.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rol_id", "permiso_id", name="uq_rol_permiso_rol_permiso"),
    )
    op.create_index(op.f("ix_rol_permiso_permiso_id"), "rol_permiso", ["permiso_id"], unique=False)
    op.create_index(op.f("ix_rol_permiso_rol_id"), "rol_permiso", ["rol_id"], unique=False)
    op.create_index(op.f("ix_rol_permiso_tenant_id"), "rol_permiso", ["tenant_id"], unique=False)

    # ------------------------------------------------------------------
    # 4. Seed idempotente — roles y permisos base para cada tenant existente
    # ------------------------------------------------------------------
    bind = op.get_bind()
    now = _utc_now()

    # Obtener todos los tenants existentes
    tenant_rows = bind.execute(sa.text("SELECT id FROM tenant")).fetchall()
    tenant_ids = [row[0] for row in tenant_rows]

    for tenant_id in tenant_ids:
        # Insertar permisos del catálogo base
        perm_id_by_name: dict[str, str] = {}
        for perm_name in ALL_PERMISSIONS:
            perm_id = str(uuid.uuid4())
            perm_id_by_name[perm_name] = perm_id
            bind.execute(
                sa.text(
                    "INSERT INTO permiso (id, tenant_id, nombre, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :nombre, :created_at, :updated_at) "
                    "ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING"
                ),
                {
                    "id": perm_id,
                    "tenant_id": str(tenant_id),
                    "nombre": perm_name,
                    "created_at": now,
                    "updated_at": now,
                },
            )

        # Re-leer IDs reales (ON CONFLICT DO NOTHING puede haber ignorado algunos)
        existing_perms = bind.execute(
            sa.text("SELECT nombre, id FROM permiso WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        ).fetchall()
        real_perm_id: dict[str, str] = {row[0]: str(row[1]) for row in existing_perms}

        # Insertar roles del dominio
        rol_id_by_name: dict[str, str] = {}
        for rol_nombre, rol_desc in DOMAIN_ROLES:
            rol_id = str(uuid.uuid4())
            rol_id_by_name[rol_nombre] = rol_id
            bind.execute(
                sa.text(
                    "INSERT INTO rol (id, tenant_id, nombre, descripcion, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :nombre, :descripcion, :created_at, :updated_at) "
                    "ON CONFLICT ON CONSTRAINT uq_rol_tenant_nombre DO NOTHING"
                ),
                {
                    "id": rol_id,
                    "tenant_id": str(tenant_id),
                    "nombre": rol_nombre,
                    "descripcion": rol_desc,
                    "created_at": now,
                    "updated_at": now,
                },
            )

        # Re-leer IDs reales de roles
        existing_roles = bind.execute(
            sa.text("SELECT nombre, id FROM rol WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        ).fetchall()
        real_rol_id: dict[str, str] = {row[0]: str(row[1]) for row in existing_roles}

        # Insertar asignaciones rol → permiso
        for rol_nombre, perm_names in ROL_PERMISOS.items():
            if rol_nombre not in real_rol_id:
                continue
            r_id = real_rol_id[rol_nombre]
            for perm_name in perm_names:
                if perm_name not in real_perm_id:
                    continue
                p_id = real_perm_id[perm_name]
                bind.execute(
                    sa.text(
                        "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at, updated_at) "
                        "VALUES (:id, :tenant_id, :rol_id, :permiso_id, :created_at, :updated_at) "
                        "ON CONFLICT ON CONSTRAINT uq_rol_permiso_rol_permiso DO NOTHING"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "rol_id": r_id,
                        "permiso_id": p_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                )


def downgrade() -> None:
    # Drop in reverse FK order
    op.drop_index(op.f("ix_rol_permiso_tenant_id"), table_name="rol_permiso")
    op.drop_index(op.f("ix_rol_permiso_rol_id"), table_name="rol_permiso")
    op.drop_index(op.f("ix_rol_permiso_permiso_id"), table_name="rol_permiso")
    op.drop_table("rol_permiso")

    op.drop_index(op.f("ix_permiso_tenant_id"), table_name="permiso")
    op.drop_table("permiso")

    op.drop_index(op.f("ix_rol_tenant_id"), table_name="rol")
    op.drop_table("rol")
