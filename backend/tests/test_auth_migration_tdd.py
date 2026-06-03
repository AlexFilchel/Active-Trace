import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def inspect_auth_database(database_url: str) -> dict[str, object]:
    engine = create_async_engine(database_url)

    async with engine.connect() as connection:
        def _inspect(sync_connection):
            inspector = inspect(sync_connection)
            tables = inspector.get_table_names()
            return {
                "tables": tables,
                "columns": {
                    table_name: {column["name"] for column in inspector.get_columns(table_name)}
                    for table_name in tables
                },
                "foreign_keys": {
                    table_name: inspector.get_foreign_keys(table_name)
                    for table_name in tables
                },
            }

        return await connection.run_sync(_inspect)


async def reset_auth_migration_state(database_url: str) -> None:
    from app.core.database import dispose_database

    await dispose_database()
    engine = create_async_engine(database_url)

    async with engine.begin() as connection:
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_password_reset_token CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_login_challenge CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_totp_credential CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_refresh_session CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS auth_user CASCADE")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        await connection.exec_driver_sql("DROP TABLE IF EXISTS tenant CASCADE")

    await engine.dispose()


def test_auth_migration_creates_expected_tables_and_foreign_keys(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_auth_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")

    metadata = asyncio.run(inspect_auth_database(settings.database_url.unicode_string()))

    assert set(metadata["tables"]) >= {
        "tenant",
        "auth_user",
        "auth_refresh_session",
        "auth_totp_credential",
        "auth_login_challenge",
        "auth_password_reset_token",
    }
    assert metadata["columns"]["auth_user"] >= {
        "id",
        "tenant_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "email",
        "password_hash",
        "roles",
        "is_active",
    }
    assert metadata["columns"]["auth_refresh_session"] >= {
        "id",
        "tenant_id",
        "user_id",
        "family_id",
        "token_hash",
        "expires_at",
        "used_at",
        "revoked_at",
        "replaced_by_session_id",
    }
    assert metadata["columns"]["auth_totp_credential"] >= {
        "tenant_id",
        "user_id",
        "secret_encrypted",
        "is_enabled",
        "confirmed_at",
    }
    assert metadata["columns"]["auth_login_challenge"] >= {
        "tenant_id",
        "user_id",
        "challenge_hash",
        "expires_at",
        "consumed_at",
    }
    assert metadata["columns"]["auth_password_reset_token"] >= {
        "tenant_id",
        "user_id",
        "token_hash",
        "expires_at",
        "consumed_at",
    }
    assert {fk["referred_table"] for fk in metadata["foreign_keys"]["auth_user"]} == {"tenant"}
    assert {fk["referred_table"] for fk in metadata["foreign_keys"]["auth_refresh_session"]} >= {"tenant", "auth_user"}
    assert {fk["referred_table"] for fk in metadata["foreign_keys"]["auth_totp_credential"]} >= {"tenant", "auth_user"}
    assert {fk["referred_table"] for fk in metadata["foreign_keys"]["auth_login_challenge"]} >= {"tenant", "auth_user"}
    assert {fk["referred_table"] for fk in metadata["foreign_keys"]["auth_password_reset_token"]} >= {"tenant", "auth_user"}


def test_auth_migration_downgrades_cleanly_and_is_sequentially_named(valid_env):
    from app.core.config import get_settings

    settings = get_settings()
    config = build_alembic_config(settings.database_url.unicode_string())

    asyncio.run(reset_auth_migration_state(settings.database_url.unicode_string()))
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    metadata = asyncio.run(inspect_auth_database(settings.database_url.unicode_string()))
    migration_file = BACKEND_ROOT / "alembic" / "versions" / "002_auth_jwt_2fa.py"

    assert "auth_user" not in metadata["tables"]
    assert "auth_refresh_session" not in metadata["tables"]
    assert migration_file.exists()
    assert migration_file.stem == "002_auth_jwt_2fa"
