from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def reset_full_state(database_url: str) -> None:
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


def test_comunicaciones_migration_crea_tabla_y_seed(valid_env):
    from app.core.config import get_settings

    db_url = get_settings().database_url.unicode_string()
    config = build_alembic_config(db_url)

    asyncio.run(reset_full_state(db_url))
    command.upgrade(config, "001_tenant")

    engine_seed = create_async_engine(db_url)

    async def seed_tenant() -> None:
        async with engine_seed.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO tenant (id, name, slug, status, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 'Tenant Comunicaciones', 'tenant-comunicaciones', 'active', NOW(), NOW())"
                )
            )

    asyncio.run(seed_tenant())
    asyncio.run(engine_seed.dispose())
    command.upgrade(config, "head")

    engine = create_async_engine(db_url)

    async def assert_db_state() -> None:
        async with engine.connect() as conn:
            def _inspect(sync_conn):
                inspector = inspect(sync_conn)
                return inspector.get_table_names(), {col["name"] for col in inspector.get_columns("comunicacion")}

            tables, columns = await conn.run_sync(_inspect)
            assert "comunicacion" in tables
            assert columns >= {
                "id",
                "tenant_id",
                "materia_id",
                "entrada_padron_id",
                "enviado_por",
                "destinatario_encrypted",
                "estado",
                "lote_id",
                "idempotency_key",
                "requiere_aprobacion",
                "intentos",
            }
            rows_enviar = await conn.execute(text("SELECT COUNT(*) FROM permiso WHERE nombre = 'comunicacion:enviar'"))
            rows_aprobar = await conn.execute(text("SELECT COUNT(*) FROM permiso WHERE nombre = 'comunicacion:aprobar'"))
            assert rows_enviar.scalar() == 1
            assert rows_aprobar.scalar() == 1

    asyncio.run(assert_db_state())
    asyncio.run(engine.dispose())
