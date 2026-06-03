import pytest
from sqlalchemy import text
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_database_session_executes_select_one(db_session):
    result = await db_session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_database_engine_reinitializes_cleanly_between_tests(valid_env):
    from app.main import create_app

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


@pytest.mark.asyncio
async def test_get_db_closes_session_after_exception(monkeypatch, valid_env):
    from app.core.dependencies import get_db
    from app.core import dependencies

    events: list[str] = []

    class FakeSession:
        async def close(self) -> None:
            events.append("closed")

    def fake_session_factory():
        return FakeSession()

    monkeypatch.setattr(dependencies, "get_session_factory", lambda: fake_session_factory)

    db_stream = get_db()
    session = None

    with pytest.raises(RuntimeError):
        session = await anext(db_stream)
        try:
            raise RuntimeError("boom")
        finally:
            await db_stream.aclose()

    assert session is not None
    assert events == ["closed"]
