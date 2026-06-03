from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, Header, Query
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import get_session_factory, initialize_database
from app.core.security import create_access_token, hash_password
from app.models import AuthRefreshSession, AuthUser, Tenant


@pytest.fixture
async def dependency_test_app(valid_env):
    from app.core.dependencies import get_current_user
    from app.repositories import AuthUserRepository

    engine = initialize_database()
    async with engine.begin() as connection:
        await connection.run_sync(Tenant.__table__.create, checkfirst=True)
        await connection.run_sync(AuthUser.__table__.create, checkfirst=True)
        await connection.run_sync(AuthRefreshSession.__table__.create, checkfirst=True)

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

        tenant_a = Tenant(name="Tenant A", slug="tenant-dep-a")
        tenant_b = Tenant(name="Tenant B", slug="tenant-dep-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        user_a = AuthUser(
            tenant_id=tenant_a.id,
            email="a@example.com",
            password_hash=hash_password("CorrectPass1!"),
            roles=["ADMIN"],
            is_active=True,
        )
        user_b = AuthUser(
            tenant_id=tenant_b.id,
            email="b@example.com",
            password_hash=hash_password("CorrectPass1!"),
            roles=["PROFESOR"],
            is_active=True,
        )
        session.add_all(
            [
                user_a,
                user_b,
            ]
        )
        await session.commit()

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(
        current_user=Depends(get_current_user),
        tenant_id: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        x_user_id: str | None = Header(default=None),
    ):
        return {
            "user_id": str(current_user.user_id),
            "tenant_id": str(current_user.tenant_id),
            "roles": current_user.roles,
            "ignored": {"tenant_id": tenant_id, "user_id": user_id, "x_user_id": x_user_id},
        }

    @app.get("/tenant-users")
    async def tenant_users(current_user=Depends(get_current_user), tenant_id: str | None = Query(default=None)):
        async with session_factory() as session:
            repository = AuthUserRepository(session=session, tenant_id=current_user.tenant_id)
            rows = await repository.list()
            return {"count": len(rows), "tenant_id": str(current_user.tenant_id), "ignored": tenant_id}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, tenant_a, tenant_b, user_a, user_b


@pytest.mark.asyncio
async def test_get_current_user_resolves_identity_only_from_verified_jwt(dependency_test_app):
    client, tenant_a, tenant_b, user_a, _user_b = dependency_test_app
    token = create_access_token(user_id=str(user_a.id), tenant_id=str(tenant_a.id), roles=["ADMIN"])
    response = await client.get(
        "/whoami?tenant_id=override-tenant&user_id=override-user",
        headers={"Authorization": f"Bearer {token}", "X-User-Id": str(tenant_b.id)},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user_a.id)
    assert response.json()["tenant_id"] == str(tenant_a.id)
    assert response.json()["roles"] == ["ADMIN"]


@pytest.mark.asyncio
async def test_missing_or_invalid_token_is_rejected_and_tenant_scope_stays_from_jwt(dependency_test_app):
    client, tenant_a, tenant_b, user_a, _user_b = dependency_test_app
    token = create_access_token(user_id=str(user_a.id), tenant_id=str(tenant_a.id), roles=["ADMIN"])
    missing = await client.get("/whoami")
    invalid = await client.get("/whoami", headers={"Authorization": "Bearer invalid-token"})
    scoped = await client.get(
        f"/tenant-users?tenant_id={tenant_b.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert scoped.status_code == 200
    assert scoped.json() == {"count": 1, "tenant_id": str(tenant_a.id), "ignored": str(tenant_b.id)}
