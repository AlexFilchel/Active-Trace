import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Tenant


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def inspect_database(database_url: str) -> tuple[list[str], list[dict[str, object]]]:
    engine = create_async_engine(database_url)

    async with engine.connect() as connection:
        table_names = await connection.run_sync(lambda sync_connection: inspect(sync_connection).get_table_names())
        tenant_columns = []
        if "tenant" in table_names:
            tenant_columns = await connection.run_sync(lambda sync_connection: inspect(sync_connection).get_columns("tenant"))

    await engine.dispose()
    return table_names, tenant_columns


async def reset_migration_state(database_url: str) -> None:
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


def test_baseline_migration_creates_tenant_table(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")

    table_names, tenant_columns = asyncio.run(inspect_database(settings.database_url.unicode_string()))

    assert "tenant" in table_names
    assert {column["name"] for column in tenant_columns} >= {"id", "created_at", "updated_at", "deleted_at", "slug", "name", "status"}
    assert set(Tenant.__table__.columns.keys()) == {column["name"] for column in tenant_columns}


def test_baseline_migration_downgrades_cleanly_and_follows_sequential_naming(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    table_names, _ = asyncio.run(inspect_database(settings.database_url.unicode_string()))
    migration_file = BACKEND_ROOT / "alembic" / "versions" / "001_tenant.py"

    assert "tenant" not in table_names
    assert migration_file.exists()
    assert migration_file.stem == "001_tenant"
