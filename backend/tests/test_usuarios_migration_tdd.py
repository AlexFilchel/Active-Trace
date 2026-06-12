from __future__ import annotations

import asyncio
from pathlib import Path
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


async def reset_state(database_url: str) -> None:
    from app.core.database import dispose_database

    await dispose_database()
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        for table_name in [
            "calificacion",
            "umbral_materia",
            "entrada_padron",
            "version_padron",
            "asignacion",
            "usuario",
            "audit_log",
            "cohorte",
            "carrera",
            "materia",
            "rol_permiso",
            "permiso",
            "rol",
            "auth_password_reset_token",
            "auth_login_challenge",
            "auth_totp_credential",
            "auth_refresh_session",
            "auth_user",
            "alembic_version",
            "tenant",
        ]:
            await conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table_name} CASCADE")
    await engine.dispose()


async def inspect_database(database_url: str) -> dict[str, object]:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        def _inspect(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            return {
                "tables": tables,
                "columns": {table: {column["name"] for column in inspector.get_columns(table)} for table in tables},
            }
        result = await conn.run_sync(_inspect)
    await engine.dispose()
    return result


async def count_permissions(database_url: str, permission_name: str) -> int:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM permiso WHERE nombre = :name"), {"name": permission_name})
        count = result.scalar_one()
    await engine.dispose()
    return count


async def count_role_permission(database_url: str, role_name: str, permission_name: str) -> int:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) "
                "FROM rol_permiso rp "
                "JOIN rol r ON r.id = rp.rol_id "
                "JOIN permiso p ON p.id = rp.permiso_id "
                "WHERE r.nombre = :role_name AND p.nombre = :permission_name"
            ),
            {"role_name": role_name, "permission_name": permission_name},
        )
        count = result.scalar_one()
    await engine.dispose()
    return count


async def count_permission_relations(database_url: str, permission_name: str) -> int:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) "
                "FROM rol_permiso rp "
                "JOIN permiso p ON p.id = rp.permiso_id "
                "WHERE p.nombre = :permission_name"
            ),
            {"permission_name": permission_name},
        )
        count = result.scalar_one()
    await engine.dispose()
    return count


async def create_tenant_for_seed(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenant (id, name, slug, status, created_at, updated_at) "
                "VALUES (:id, 'Seed Tenant', :slug, 'active', NOW(), NOW())"
            ),
            {"id": str(uuid.uuid4()), "slug": f"seed-tenant-{uuid.uuid4()}"},
        )
    await engine.dispose()


def test_migration_005_creates_usuario_and_asignacion_and_is_idempotent(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.database_url.unicode_string()
    config = build_alembic_config(db_url)

    asyncio.run(reset_state(db_url))
    command.upgrade(config, "001_tenant")
    asyncio.run(create_tenant_for_seed(db_url))
    command.upgrade(config, "head")
    meta = asyncio.run(inspect_database(db_url))

    assert "usuario" in meta["tables"]
    assert "asignacion" in meta["tables"]
    assert meta["columns"]["usuario"] >= {"auth_user_id", "email_encrypted", "email_hash", "dni_encrypted", "estado"}
    assert meta["columns"]["asignacion"] >= {"usuario_id", "rol_id", "materia_id", "carrera_id", "cohorte_id", "responsable_id", "desde", "hasta"}
    assert asyncio.run(count_role_permission(db_url, "ADMIN", "usuarios:gestionar")) >= 1
    assert asyncio.run(count_role_permission(db_url, "ADMIN", "equipos:asignar")) >= 1
    assert asyncio.run(count_role_permission(db_url, "COORDINADOR", "equipos:asignar")) >= 1

    first_users_permission = asyncio.run(count_permissions(db_url, "usuarios:gestionar"))
    first_assign_permission = asyncio.run(count_permissions(db_url, "equipos:asignar"))
    command.downgrade(config, "004_estructura_academica")
    assert asyncio.run(count_permissions(db_url, "usuarios:gestionar")) == 0
    assert asyncio.run(count_permissions(db_url, "equipos:asignar")) == 0
    assert asyncio.run(count_permission_relations(db_url, "usuarios:gestionar")) == 0
    assert asyncio.run(count_permission_relations(db_url, "equipos:asignar")) == 0
    command.upgrade(config, "head")

    assert asyncio.run(count_permissions(db_url, "usuarios:gestionar")) == first_users_permission
    assert asyncio.run(count_permissions(db_url, "equipos:asignar")) == first_assign_permission
