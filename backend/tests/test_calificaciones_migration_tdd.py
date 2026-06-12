"""TDD: 007_calificaciones migration — creates calificacion + umbral_materia, downgrade removes them."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def reset_cal_migration_state(database_url: str) -> None:
    from app.core.database import dispose_database

    await dispose_database()
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP TABLE IF EXISTS calificacion CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS umbral_materia CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS entrada_padron CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS version_padron CASCADE")
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
        await conn.exec_driver_sql("DROP FUNCTION IF EXISTS audit_log_immutable_fn")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS audit_log CASCADE")
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
        await conn.exec_driver_sql("DROP TABLE IF EXISTS test_sample_tenant_record CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS test_repository_record CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS tenant CASCADE")

    await engine.dispose()


async def get_tables(database_url: str) -> list[str]:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    await engine.dispose()
    return tables


def test_007_calificaciones_creates_calificacion_and_umbral_materia(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_cal_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")

    tables = asyncio.run(get_tables(settings.database_url.unicode_string()))
    assert "calificacion" in tables
    assert "umbral_materia" in tables


def test_007_calificaciones_downgrade_removes_calificacion_and_umbral_materia(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_cal_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")
    command.downgrade(config, "006_padron")

    tables = asyncio.run(get_tables(settings.database_url.unicode_string()))
    assert "calificacion" not in tables
    assert "umbral_materia" not in tables
    assert "entrada_padron" in tables


def test_007_downgrade_does_not_affect_earlier_tables(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_cal_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")
    command.downgrade(config, "006_padron")

    tables = asyncio.run(get_tables(settings.database_url.unicode_string()))
    assert "tenant" in tables
    assert "usuario" in tables
    assert "audit_log" in tables
