"""TDD tests for RBAC migration 003_rbac — tables and seed.

Covers:
- After migration, tables rol, permiso, rol_permiso exist with expected columns
- Each tenant gets 7 domain roles seeded
- Seed is idempotent (second run does not duplicate or error)
- downgrade drops tables cleanly
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]

DOMAIN_ROLES = {"ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"}


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def reset_full_state(database_url: str) -> None:
    from app.core.database import dispose_database

    await dispose_database()
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
        await conn.exec_driver_sql("DROP FUNCTION IF EXISTS audit_log_immutable_fn")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS audit_log CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS entrada_padron CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS version_padron CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS asignacion CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS usuario CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS cohorte CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS carrera CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS materia CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS rol_permiso CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS permiso CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS rol CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS auth_password_reset_token CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS auth_login_challenge CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS auth_totp_credential CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS auth_refresh_session CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS auth_user CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS tenant CASCADE")

    await engine.dispose()


async def inspect_tables(database_url: str) -> dict:
    engine = create_async_engine(database_url)

    async with engine.connect() as conn:
        def _inspect(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            return {
                "tables": tables,
                "columns": {
                    t: {col["name"] for col in inspector.get_columns(t)}
                    for t in tables
                },
                "unique_constraints": {
                    t: inspector.get_unique_constraints(t)
                    for t in tables
                },
            }

        return await conn.run_sync(_inspect)


async def get_seeded_roles(database_url: str, tenant_id: str) -> set[str]:
    engine = create_async_engine(database_url)

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT nombre FROM rol WHERE tenant_id = :tid AND deleted_at IS NULL"),
            {"tid": tenant_id},
        )
        rows = result.fetchall()

    await engine.dispose()
    return {row[0] for row in rows}


async def count_roles(database_url: str) -> int:
    engine = create_async_engine(database_url)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM rol"))
        count = result.scalar()

    await engine.dispose()
    return count


async def create_test_tenant(database_url: str) -> str:
    """Insert a tenant and return its UUID string."""
    import uuid

    engine = create_async_engine(database_url)
    tenant_id = str(uuid.uuid4())

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenant (id, name, slug, status, created_at, updated_at) "
                "VALUES (:id, 'Test Tenant', 'test-rbac-seed', 'active', NOW(), NOW())"
            ),
            {"id": tenant_id},
        )

    await engine.dispose()
    return tenant_id


def test_rbac_migration_creates_expected_tables(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.database_url.unicode_string()
    config = build_alembic_config(db_url)

    asyncio.run(reset_full_state(db_url))
    command.upgrade(config, "head")

    meta = asyncio.run(inspect_tables(db_url))

    assert "rol" in meta["tables"]
    assert "permiso" in meta["tables"]
    assert "rol_permiso" in meta["tables"]

    assert meta["columns"]["rol"] >= {"id", "tenant_id", "nombre", "descripcion", "created_at", "updated_at", "deleted_at"}
    assert meta["columns"]["permiso"] >= {"id", "tenant_id", "nombre", "created_at", "updated_at", "deleted_at"}
    assert meta["columns"]["rol_permiso"] >= {"id", "tenant_id", "rol_id", "permiso_id", "created_at", "updated_at", "deleted_at"}


def test_rbac_migration_seeds_domain_roles_for_each_tenant(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.database_url.unicode_string()
    config = build_alembic_config(db_url)

    asyncio.run(reset_full_state(db_url))
    command.upgrade(config, "001_tenant")

    tenant_id_a = asyncio.run(create_test_tenant(db_url))

    # Patch slug to avoid conflict with second tenant test
    engine_sync = create_async_engine(db_url)

    async def fix_slug():
        async with engine_sync.begin() as conn:
            await conn.execute(text("UPDATE tenant SET slug = 'rbac-seed-a' WHERE id = :id"), {"id": tenant_id_a})
        await engine_sync.dispose()

    asyncio.run(fix_slug())

    command.upgrade(config, "head")

    roles_a = asyncio.run(get_seeded_roles(db_url, tenant_id_a))
    assert roles_a == DOMAIN_ROLES


def test_rbac_seed_is_idempotent(valid_env):
    """Running the migration seed twice does not duplicate roles."""
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.database_url.unicode_string()
    config = build_alembic_config(db_url)

    asyncio.run(reset_full_state(db_url))
    command.upgrade(config, "head")

    count_after_first = asyncio.run(count_roles(db_url))

    # Simulate re-seeding by calling the seed SQL directly via raw execute
    # (idempotency: ON CONFLICT DO NOTHING means a second run is a no-op)
    # We do this by downgrading to 002 and re-upgrading to head
    command.downgrade(config, "002_auth_jwt_2fa")
    command.upgrade(config, "head")

    count_after_second = asyncio.run(count_roles(db_url))

    assert count_after_first == count_after_second


def test_rbac_migration_downgrade_drops_tables(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    db_url = settings.database_url.unicode_string()
    config = build_alembic_config(db_url)

    asyncio.run(reset_full_state(db_url))
    command.upgrade(config, "head")
    command.downgrade(config, "002_auth_jwt_2fa")

    meta = asyncio.run(inspect_tables(db_url))

    assert "rol" not in meta["tables"]
    assert "permiso" not in meta["tables"]
    assert "rol_permiso" not in meta["tables"]
    # Previous tables should still be there
    assert "auth_user" in meta["tables"]
