from httpx import ASGITransport, AsyncClient


async def test_health_reports_app_and_database_up(valid_env):
    from app.main import create_app

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


async def test_health_reports_database_down_without_crashing(valid_env):
    from app.api.v1.routers import health
    from app.main import create_app

    class FailingSession:
        async def execute(self, *_args, **_kwargs):
            raise RuntimeError("db down")

    async def override_get_db():
        yield FailingSession()

    app = create_app()
    app.dependency_overrides[health.get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "down"}
