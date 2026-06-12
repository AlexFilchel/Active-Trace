"""TDD tests for impersonation feature.

Covers (spec requirements):
- Without impersonacion:usar permission → 403
- With permission → token with claim impersonating_user_id
- Impersonation token has user_id = actor_real
- IMPERSONACION_INICIAR is logged on start
- IMPERSONACION_FINALIZAR is logged on end (POST /api/auth/impersonate/end)
- Actions under impersonation have actor_id = actor_real, impersonado_id = target
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import get_session_factory, initialize_database
from app.core.security import create_access_token, decode_access_token, hash_password
from app.models import AuditLog, AuthUser, Permiso, Rol, RolPermiso, Tenant
from app.models.auth import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential
from app.models.usuarios import Asignacion, Usuario


@pytest.fixture
async def impersonation_app(valid_env):
    """Set up a FastAPI app with impersonation endpoints and RBAC data."""
    from app.api.v1.routers.auth import router
    from app.models.audit import AuditLog as AuditLogModel

    engine = initialize_database()
    async with engine.begin() as conn:
        await conn.run_sync(Tenant.__table__.create, checkfirst=True)
        await conn.run_sync(AuthUser.__table__.create, checkfirst=True)
        await conn.run_sync(AuthRefreshSession.__table__.create, checkfirst=True)
        await conn.run_sync(AuthTotpCredential.__table__.create, checkfirst=True)
        await conn.run_sync(AuthLoginChallenge.__table__.create, checkfirst=True)
        await conn.run_sync(AuthPasswordResetToken.__table__.create, checkfirst=True)
        await conn.run_sync(Rol.__table__.create, checkfirst=True)
        await conn.run_sync(Permiso.__table__.create, checkfirst=True)
        await conn.run_sync(RolPermiso.__table__.create, checkfirst=True)
        await conn.run_sync(AuditLogModel.__table__.create, checkfirst=True)

    session_factory = get_session_factory()
    async with session_factory() as session:
        # TRUNCATE audit_log first (bypasses row-level trigger), then FK deps
        from sqlalchemy import text
        await session.execute(text("TRUNCATE TABLE audit_log"))
        await session.execute(delete(Asignacion))
        await session.execute(delete(RolPermiso))
        await session.execute(delete(Permiso))
        await session.execute(delete(Rol))
        await session.execute(delete(Usuario))
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

        tenant = Tenant(name="Impersonation Test", slug="impersonation-test")
        session.add(tenant)
        await session.flush()

        # Admin user — has impersonacion:usar
        admin = AuthUser(
            tenant_id=tenant.id,
            email="admin@imp.test",
            password_hash=hash_password("Pass1!"),
            roles=["ADMIN"],
            is_active=True,
        )
        # Target user — will be impersonated
        target = AuthUser(
            tenant_id=tenant.id,
            email="target@imp.test",
            password_hash=hash_password("Pass1!"),
            roles=["ALUMNO"],
            is_active=True,
        )
        # Regular user — no impersonacion:usar
        regular = AuthUser(
            tenant_id=tenant.id,
            email="regular@imp.test",
            password_hash=hash_password("Pass1!"),
            roles=["ALUMNO"],
            is_active=True,
        )
        session.add_all([admin, target, regular])
        await session.flush()

        # Set up RBAC: ADMIN role with impersonacion:usar
        rol_admin = Rol(tenant_id=tenant.id, nombre="ADMIN")
        rol_alumno = Rol(tenant_id=tenant.id, nombre="ALUMNO")
        session.add_all([rol_admin, rol_alumno])
        await session.flush()

        p_impersonate = Permiso(tenant_id=tenant.id, nombre="impersonacion:usar")
        session.add(p_impersonate)
        await session.flush()

        rp = RolPermiso(tenant_id=tenant.id, rol_id=rol_admin.id, permiso_id=p_impersonate.id)
        session.add(rp)
        await session.commit()

        # Build tokens
        token_admin = create_access_token(
            user_id=str(admin.id),
            tenant_id=str(tenant.id),
            roles=["ADMIN"],
        )
        token_regular = create_access_token(
            user_id=str(regular.id),
            tenant_id=str(tenant.id),
            roles=["ALUMNO"],
        )

        app = FastAPI()
        app.include_router(router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield client, token_admin, token_regular, admin, target, tenant, session


@pytest.mark.asyncio
async def test_impersonate_without_permission_returns_403(impersonation_app):
    """User without impersonacion:usar gets 403 from POST /api/auth/impersonate/{user_id}."""
    client, _, token_regular, _, target, _, _ = impersonation_app

    response = await client.post(
        f"/api/auth/impersonate/{target.id}",
        headers={"Authorization": f"Bearer {token_regular}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_impersonate_with_permission_returns_token_with_claim(impersonation_app):
    """User with impersonacion:usar gets a token with impersonating_user_id claim."""
    client, token_admin, _, _, target, _, _ = impersonation_app

    response = await client.post(
        f"/api/auth/impersonate/{target.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    claims = decode_access_token(data["access_token"])
    assert str(claims["impersonating_user_id"]) == str(target.id)


@pytest.mark.asyncio
async def test_impersonation_token_has_actor_as_user_id(impersonation_app):
    """The impersonation token's user_id is the real actor, NOT the impersonated user."""
    client, token_admin, _, admin, target, _, _ = impersonation_app

    response = await client.post(
        f"/api/auth/impersonate/{target.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    assert response.status_code == 200
    claims = decode_access_token(response.json()["access_token"])
    assert str(claims["user_id"]) == str(admin.id)


@pytest.mark.asyncio
async def test_impersonacion_iniciar_is_logged(impersonation_app):
    """IMPERSONACION_INICIAR is recorded in audit_log when impersonation starts."""
    client, token_admin, _, admin, target, tenant, session = impersonation_app

    await client.post(
        f"/api/auth/impersonate/{target.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    entry = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant.id)
        .where(AuditLog.accion == "IMPERSONACION_INICIAR")
    )

    assert entry is not None
    assert entry.actor_id == admin.id
    assert entry.impersonado_id == target.id


@pytest.mark.asyncio
async def test_impersonacion_finalizar_is_logged(impersonation_app):
    """IMPERSONACION_FINALIZAR is recorded when POST /api/auth/impersonate/end is called."""
    client, token_admin, _, admin, target, tenant, session = impersonation_app

    # Start impersonation
    start_response = await client.post(
        f"/api/auth/impersonate/{target.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert start_response.status_code == 200
    impersonation_token = start_response.json()["access_token"]

    # End impersonation using the impersonation token
    end_response = await client.post(
        "/api/auth/impersonate/end",
        headers={"Authorization": f"Bearer {impersonation_token}"},
    )

    assert end_response.status_code == 204

    entry = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant.id)
        .where(AuditLog.accion == "IMPERSONACION_FINALIZAR")
    )

    assert entry is not None
    assert entry.actor_id == admin.id
    assert entry.impersonado_id == target.id
