from httpx import ASGITransport, AsyncClient


async def test_application_starts_and_serves_requests(valid_env):
    from app.main import create_app

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
