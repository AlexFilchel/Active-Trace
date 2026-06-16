"""TDD tests for append-only enforcement on audit_log at DB level.

Covers (spec requirements):
- UPDATE directly on the audit_log table is rejected by the trigger
- DELETE directly on the audit_log table is rejected by the trigger

These tests run the migration to ensure the trigger exists.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def reset_audit_migration_state(database_url: str) -> None:
    from app.core.database import dispose_database
    from sqlalchemy import text

    await dispose_database()
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
        await conn.exec_driver_sql("DROP FUNCTION IF EXISTS audit_log_immutable_fn CASCADE")
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        for (table,) in result.fetchall():
            await conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    await engine.dispose()

    await engine.dispose()


async def setup_audit_log_with_trigger(database_url: str) -> tuple[str, str]:
    """Run migrations and insert a test record. Returns (tenant_id, audit_id)."""
    from app.core.database import dispose_database

    await dispose_database()
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        import uuid
        from datetime import datetime, timezone

        tenant_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await conn.execute(
            text(
                "INSERT INTO tenant (id, name, slug, status, created_at, updated_at) "
                "VALUES (:id, :name, :slug, 'active', :now, :now)"
            ),
            {"id": tenant_id, "name": "Trigger Test Tenant", "slug": "trigger-test", "now": now},
        )
        await conn.execute(
            text(
                "INSERT INTO auth_user (id, tenant_id, email, password_hash, roles, is_active, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :email, :pw, '[]'::jsonb, true, :now, :now)"
            ),
            {
                "id": user_id,
                "tenant_id": tenant_id,
                "email": "trigger@test.com",
                "pw": "hash",
                "now": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO audit_log (id, tenant_id, actor_id, accion, filas_afectadas, fecha_hora) "
                "VALUES (:id, :tenant_id, :actor_id, 'TEST_ACTION', 0, :now)"
            ),
            {"id": audit_id, "tenant_id": tenant_id, "actor_id": user_id, "now": now},
        )

    await engine.dispose()
    return tenant_id, audit_id


def test_audit_log_trigger_rejects_update(valid_env):
    """UPDATE directly on audit_log table is rejected by DB trigger."""
    from app.core.config import get_settings

    settings = get_settings()
    database_url = settings.database_url.unicode_string()
    config = build_alembic_config(database_url)

    asyncio.run(reset_audit_migration_state(database_url))
    command.upgrade(config, "head")

    _, audit_id = asyncio.run(setup_audit_log_with_trigger(database_url))

    engine = create_async_engine(database_url)

    async def attempt_update():
        async with engine.connect() as conn:
            await conn.execute(
                text("UPDATE audit_log SET accion = 'HACKED' WHERE id = :id"),
                {"id": audit_id},
            )

    import asyncio as _asyncio

    try:
        with pytest.raises(Exception, match="audit_log is append-only"):
            _asyncio.run(attempt_update())
    finally:
        _asyncio.run(engine.dispose())
        # The trigger blocks UPDATE/DELETE, so the inserted rows can only be
        # removed via DROP TABLE CASCADE — leaving them would FK-violate any
        # later test that does a plain DELETE FROM auth_user/tenant.
        asyncio.run(reset_audit_migration_state(database_url))


def test_audit_log_trigger_rejects_delete(valid_env):
    """DELETE directly on audit_log table is rejected by DB trigger."""
    from app.core.config import get_settings

    settings = get_settings()
    database_url = settings.database_url.unicode_string()
    config = build_alembic_config(database_url)

    asyncio.run(reset_audit_migration_state(database_url))
    command.upgrade(config, "head")

    _, audit_id = asyncio.run(setup_audit_log_with_trigger(database_url))

    engine = create_async_engine(database_url)

    async def attempt_delete():
        async with engine.connect() as conn:
            await conn.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": audit_id},
            )

    import asyncio as _asyncio

    try:
        with pytest.raises(Exception, match="audit_log is append-only"):
            _asyncio.run(attempt_delete())
    finally:
        _asyncio.run(engine.dispose())
        asyncio.run(reset_audit_migration_state(database_url))


def test_audit_log_migration_file_is_sequentially_named(valid_env):
    """Migration file 004_audit_log.py must exist and be sequentially named."""
    migration_file = BACKEND_ROOT / "alembic" / "versions" / "004_audit_log.py"
    assert migration_file.exists(), f"Migration file not found: {migration_file}"
    assert migration_file.stem == "004_audit_log"
