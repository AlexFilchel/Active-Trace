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

    await dispose_database()
    engine = create_async_engine(database_url)

    async with engine.begin() as connection:
        await connection.exec_driver_sql("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
        await connection.exec_driver_sql("DROP FUNCTION IF EXISTS audit_log_immutable_fn")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS audit_log CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS comunicacion CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS calificacion CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS umbral_materia CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS finalizacion_actividad CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS entrada_padron CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS version_padron CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS asignacion CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS usuario CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS cohorte CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS carrera CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS materia CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS rol_permiso CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS permiso CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS rol CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_password_reset_token CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_login_challenge CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_totp_credential CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_refresh_session CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_user CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS test_sample_tenant_record CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS test_repository_record CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS tenant CASCADE")

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
