"""liquidaciones y honorarios — DDL + seed permisos

Revision ID: 016_liquidaciones_honorarios
Revises: 015_auditoria_permiso
Create Date: 2026-06-14 00:00:00
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "016_liquidaciones_honorarios"
down_revision = "015_auditoria_permiso"
branch_labels = None
depends_on = None

_PERMISOS = (
    ("liquidaciones:ver", ("FINANZAS", "ADMIN")),
    ("liquidaciones:configurar-salarios", ("FINANZAS",)),
    ("liquidaciones:cerrar", ("FINANZAS",)),
    ("liquidaciones:gestionar-facturas", ("FINANZAS",)),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # ── Columna nueva en materia ──────────────────────────────────────────────
    op.add_column("materia", sa.Column("categoria_plus", sa.String(50), nullable=True))

    # ── salario_base ─────────────────────────────────────────────────────────
    op.create_table(
        "salario_base",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_salario_base_tenant_rol", "salario_base", ["tenant_id", "rol"])

    # ── salario_plus ──────────────────────────────────────────────────────────
    op.create_table(
        "salario_plus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("grupo", sa.String(50), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_salario_plus_tenant_grupo_rol", "salario_plus", ["tenant_id", "grupo", "rol"])

    # ── liquidacion ───────────────────────────────────────────────────────────
    op.create_table(
        "liquidacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("comisiones", postgresql.JSONB, nullable=True),
        sa.Column("monto_base", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("monto_plus", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("es_nexo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("excluido_por_factura", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("estado", sa.String(10), nullable=False, server_default="Abierta"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "cohorte_id", "periodo", "usuario_id", "rol", name="uq_liquidacion_periodo_docente_rol"),
    )
    op.create_index("ix_liquidacion_tenant_cohorte_periodo", "liquidacion", ["tenant_id", "cohorte_id", "periodo"])

    # ── factura ───────────────────────────────────────────────────────────────
    op.create_table(
        "factura",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("detalle", sa.Text, nullable=True),
        sa.Column("referencia_archivo", sa.Text, nullable=True),
        sa.Column("tamano_kb", sa.Numeric(10, 2), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="Pendiente"),
        sa.Column("cargada_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("abonada_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_factura_tenant_usuario", "factura", ["tenant_id", "usuario_id"])

    # ── Seed de permisos ──────────────────────────────────────────────────────
    conn = op.get_bind()
    now = _utc_now()
    tenant_rows = conn.execute(sa.text("SELECT id FROM tenant")).fetchall()

    for tenant_row in tenant_rows:
        tid = tenant_row[0]
        for permiso_nombre, roles in _PERMISOS:
            pid = uuid.uuid4()
            conn.execute(sa.text("""
                INSERT INTO permiso (id, tenant_id, nombre, created_at, updated_at)
                VALUES (:id, :tenant_id, :nombre, :now, :now)
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING
            """), {"id": pid, "tenant_id": tid, "nombre": permiso_nombre, "now": now})

            result = conn.execute(sa.text(
                "SELECT id FROM permiso WHERE tenant_id = :t AND nombre = :n"
            ), {"t": tid, "n": permiso_nombre}).fetchone()
            if not result:
                continue
            real_pid = result[0]

            for rol_nombre in roles:
                rol_row = conn.execute(sa.text(
                    "SELECT id FROM rol WHERE tenant_id = :t AND nombre = :r"
                ), {"t": tid, "r": rol_nombre}).fetchone()
                if not rol_row:
                    continue
                conn.execute(sa.text("""
                    INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at, updated_at)
                    VALUES (:id, :t, :rid, :pid, :now, :now)
                    ON CONFLICT DO NOTHING
                """), {"id": uuid.uuid4(), "t": tid, "rid": rol_row[0], "pid": real_pid, "now": now})


def downgrade() -> None:
    pass
