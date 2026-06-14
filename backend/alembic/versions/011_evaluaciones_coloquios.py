"""evaluaciones y coloquios

Revision ID: 011_evaluaciones_coloquios
Revises: 010_encuentros_guardias
Create Date: 2026-06-14 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "011_evaluaciones_coloquios"
down_revision = "010_encuentros_guardias"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # --- evaluacion ---
    op.create_table(
        "evaluacion",
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False, server_default="Coloquio"),
        sa.Column("instancia", sa.String(length=255), nullable=False),
        sa.Column("dias_disponibles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Abierta"),
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
    op.create_index("ix_evaluacion_tenant_id", "evaluacion", ["tenant_id"], unique=False)
    op.create_index("ix_evaluacion_materia_id", "evaluacion", ["materia_id"], unique=False)
    op.create_index("ix_evaluacion_cohorte_id", "evaluacion", ["cohorte_id"], unique=False)

    # --- dia_evaluacion ---
    op.create_table(
        "dia_evaluacion",
        sa.Column("evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cupo_total", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["evaluacion_id"], ["evaluacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dia_evaluacion_tenant_id", "dia_evaluacion", ["tenant_id"], unique=False)
    op.create_index("ix_dia_evaluacion_evaluacion_id", "dia_evaluacion", ["evaluacion_id"], unique=False)

    # --- candidato_evaluacion ---
    op.create_table(
        "candidato_evaluacion",
        sa.Column("evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alumno_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluacion_id"], ["evaluacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidato_evaluacion_tenant_id", "candidato_evaluacion", ["tenant_id"], unique=False)
    op.create_index("ix_candidato_evaluacion_evaluacion_id", "candidato_evaluacion", ["evaluacion_id"], unique=False)
    op.create_index("ix_candidato_evaluacion_alumno_id", "candidato_evaluacion", ["alumno_id"], unique=False)

    # --- reserva_evaluacion ---
    op.create_table(
        "reserva_evaluacion",
        sa.Column("evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dia_evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alumno_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dia_evaluacion_id"], ["dia_evaluacion.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluacion_id"], ["evaluacion.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reserva_evaluacion_tenant_id", "reserva_evaluacion", ["tenant_id"], unique=False)
    op.create_index("ix_reserva_evaluacion_evaluacion_id", "reserva_evaluacion", ["evaluacion_id"], unique=False)
    op.create_index("ix_reserva_evaluacion_dia_id", "reserva_evaluacion", ["dia_evaluacion_id"], unique=False)
    op.create_index("ix_reserva_evaluacion_alumno_id", "reserva_evaluacion", ["alumno_id"], unique=False)
    # Unique partial index: one active reserva per alumno per convocatoria
    op.execute(
        "CREATE UNIQUE INDEX uq_reserva_activa_alumno_evaluacion "
        "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
        "WHERE deleted_at IS NULL AND estado = 'Activa'"
    )

    # --- resultado_evaluacion ---
    op.create_table(
        "resultado_evaluacion",
        sa.Column("evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nota_final", sa.String(length=50), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alumno_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluacion_id"], ["evaluacion.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resultado_evaluacion_tenant_id", "resultado_evaluacion", ["tenant_id"], unique=False)
    op.create_index("ix_resultado_evaluacion_evaluacion_id", "resultado_evaluacion", ["evaluacion_id"], unique=False)
    op.create_index("ix_resultado_evaluacion_alumno_id", "resultado_evaluacion", ["alumno_id"], unique=False)

    # --- Seed: permiso coloquios:gestionar para COORDINADOR y ADMIN ---
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
                "nombre": "coloquios:gestionar",
                "created_at": now,
                "updated_at": now,
            },
        )
        role_rows = bind.execute(
            sa.text(
                "SELECT id, nombre FROM rol WHERE tenant_id = :tenant_id AND nombre IN ('COORDINADOR', 'ADMIN')"
            ),
            {"tenant_id": tenant_id},
        ).fetchall()
        for role_id, _role_name in role_rows:
            permiso_row = bind.execute(
                sa.text("SELECT id FROM permiso WHERE tenant_id = :tenant_id AND nombre = :nombre"),
                {"tenant_id": tenant_id, "nombre": "coloquios:gestionar"},
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
    # Remove seeded permissions
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM rol_permiso WHERE permiso_id IN "
            "(SELECT id FROM permiso WHERE nombre = 'coloquios:gestionar')"
        )
    )
    bind.execute(
        sa.text("DELETE FROM permiso WHERE nombre = 'coloquios:gestionar'")
    )

    op.execute("DROP INDEX IF EXISTS uq_reserva_activa_alumno_evaluacion")
    op.drop_index("ix_resultado_evaluacion_alumno_id", table_name="resultado_evaluacion")
    op.drop_index("ix_resultado_evaluacion_evaluacion_id", table_name="resultado_evaluacion")
    op.drop_index("ix_resultado_evaluacion_tenant_id", table_name="resultado_evaluacion")
    op.drop_table("resultado_evaluacion")

    op.drop_index("ix_reserva_evaluacion_alumno_id", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_dia_id", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_evaluacion_id", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_tenant_id", table_name="reserva_evaluacion")
    op.drop_table("reserva_evaluacion")

    op.drop_index("ix_candidato_evaluacion_alumno_id", table_name="candidato_evaluacion")
    op.drop_index("ix_candidato_evaluacion_evaluacion_id", table_name="candidato_evaluacion")
    op.drop_index("ix_candidato_evaluacion_tenant_id", table_name="candidato_evaluacion")
    op.drop_table("candidato_evaluacion")

    op.drop_index("ix_dia_evaluacion_evaluacion_id", table_name="dia_evaluacion")
    op.drop_index("ix_dia_evaluacion_tenant_id", table_name="dia_evaluacion")
    op.drop_table("dia_evaluacion")

    op.drop_index("ix_evaluacion_cohorte_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_materia_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_tenant_id", table_name="evaluacion")
    op.drop_table("evaluacion")
