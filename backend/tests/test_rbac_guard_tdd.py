"""TDD tests for require_permission guard (FastAPI dependency).

Covers:
- Usuario con permiso → 200 en endpoint protegido
- Usuario sin el permiso → 403
- Request sin Authorization header → 401
- Endpoint con permiso inexistente → 403 (fail-closed)
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import get_session_factory, initialize_database
from app.core.security import create_access_token, hash_password
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Permiso, Rol, RolPermiso, Tenant


@pytest.fixture
async def guard_test_app(valid_env):
    """Set up a FastAPI app with two protected endpoints and test data."""
    from app.core.permissions import require_permission

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

    session_factory = get_session_factory()

    async with session_factory() as session:
        # Clean up in FK order
        await session.execute(delete(RolPermiso))
        await session.execute(delete(Permiso))
        await session.execute(delete(Rol))
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

        tenant = Tenant(name="Guard Test Tenant", slug="guard-test")
        session.add(tenant)
        await session.flush()

        # User with PROFESOR role (has calificaciones:importar)
        user_profesor = AuthUser(
            tenant_id=tenant.id,
            email="profesor@guard.test",
            password_hash=hash_password("Pass1!"),
            roles=["PROFESOR"],
            is_active=True,
        )
        # User with ALUMNO role (does NOT have calificaciones:importar)
        user_alumno = AuthUser(
            tenant_id=tenant.id,
            email="alumno@guard.test",
            password_hash=hash_password("Pass1!"),
            roles=["ALUMNO"],
            is_active=True,
        )
        session.add_all([user_profesor, user_alumno])
        await session.flush()

        # Set up RBAC data
        rol_profesor = Rol(tenant_id=tenant.id, nombre="PROFESOR")
        rol_alumno = Rol(tenant_id=tenant.id, nombre="ALUMNO")
        session.add_all([rol_profesor, rol_alumno])
        await session.flush()

        p_importar = Permiso(tenant_id=tenant.id, nombre="calificaciones:importar")
        p_avisos = Permiso(tenant_id=tenant.id, nombre="avisos:confirmar")
        session.add_all([p_importar, p_avisos])
        await session.flush()

        # PROFESOR gets calificaciones:importar
        rp_prof = RolPermiso(tenant_id=tenant.id, rol_id=rol_profesor.id, permiso_id=p_importar.id)
        # ALUMNO gets avisos:confirmar only
        rp_alum = RolPermiso(tenant_id=tenant.id, rol_id=rol_alumno.id, permiso_id=p_avisos.id)
        session.add_all([rp_prof, rp_alum])
        await session.commit()

        # Build FastAPI app
        app = FastAPI()

        @app.get("/importar", dependencies=[require_permission("calificaciones:importar")])
        async def importar_endpoint():
            return {"ok": True}

        @app.get("/inexistente", dependencies=[require_permission("modulo:accion_inexistente")])
        async def inexistente_endpoint():
            return {"ok": True}

        token_profesor = create_access_token(
            user_id=str(user_profesor.id),
            tenant_id=str(tenant.id),
            roles=["PROFESOR"],
        )
        token_alumno = create_access_token(
            user_id=str(user_alumno.id),
            tenant_id=str(tenant.id),
            roles=["ALUMNO"],
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield client, token_profesor, token_alumno


@pytest.mark.asyncio
async def test_usuario_con_permiso_accede_al_endpoint_protegido(guard_test_app):
    """Usuario con calificaciones:importar obtiene 200."""
    client, token_profesor, _ = guard_test_app

    response = await client.get("/importar", headers={"Authorization": f"Bearer {token_profesor}"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_usuario_sin_permiso_recibe_403(guard_test_app):
    """Usuario con ALUMNO (sin calificaciones:importar) obtiene 403."""
    client, _, token_alumno = guard_test_app

    response = await client.get("/importar", headers={"Authorization": f"Bearer {token_alumno}"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_request_sin_authorization_header_recibe_401(guard_test_app):
    """Request sin Authorization header obtiene 401."""
    client, _, _ = guard_test_app

    response = await client.get("/importar")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_permiso_inexistente_en_seed_resulta_en_403(guard_test_app):
    """Endpoint con permiso inexistente resulta en 403 (fail-closed)."""
    client, token_profesor, _ = guard_test_app

    response = await client.get("/inexistente", headers={"Authorization": f"Bearer {token_profesor}"})

    assert response.status_code == 403
