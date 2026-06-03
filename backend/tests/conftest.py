import os

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def reset_settings_cache():
    try:
        from app.core import config
    except ModuleNotFoundError:
        yield
        return

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:123@localhost:5432/activia_trace_test"))
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("ENCRYPTION_KEY", "e" * 32)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "activia-trace-test")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)


@pytest.fixture
def invalid_db_url_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "not-a-valid-db-url")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("ENCRYPTION_KEY", "e" * 32)


@pytest_asyncio.fixture(autouse=True)
async def reset_database_state():
    try:
        from app.core.database import dispose_database
    except ModuleNotFoundError:
        yield
        return

    await dispose_database()
    yield
    await dispose_database()


@pytest_asyncio.fixture
async def db_session(valid_env):
    from app.core.database import get_session_factory

    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session
