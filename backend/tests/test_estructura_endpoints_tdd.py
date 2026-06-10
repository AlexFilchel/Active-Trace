"""TDD tests para endpoints de estructura académica.

Covers:
- Usuario sin permiso estructura:gestionar → 403
- Usuario con permiso puede crear y listar carreras
- GET de carrera de otro tenant → 404
- POST con código duplicado → 409
- DELETE → soft delete (carrera desaparece del listado)
- Crear cohorte activa en carrera inactiva → 422
- Filtro por carrera_id en cohortes
- Filtro por estado en materias
- Aislamiento tenant en materias
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import get_session_factory, initialize_database
from app.core.security import create_access_token, hash_password
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Tenant
from app.models.rbac import Permiso, Rol, RolPermiso
from app.models.estructura import Carrera, Cohorte, Materia


@pytest.fixture
async def estructura_app(valid_env):
    """FastAPI app con router de estructura y datos RBAC para dos usuarios."""
    from app.api.v1.routers.estructura import router as estructura_router

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
        await conn.run_sync(Carrera.__table__.create, checkfirst=True)
        await conn.run_sync(Cohorte.__table__.create, checkfirst=True)
        await conn.run_sync(Materia.__table__.create, checkfirst=True)

    session_factory = get_session_factory()

    async with session_factory() as session:
        await session.execute(delete(Cohorte))
        await session.execute(delete(Carrera))
        await session.execute(delete(Materia))
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

        tenant_a = Tenant(name="EndpointTenant A", slug="ep-a")
        tenant_b = Tenant(name="EndpointTenant B", slug="ep-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        # ADMIN user (has estructura:gestionar)
        user_admin = AuthUser(
            tenant_id=tenant_a.id,
            email="admin@ep.test",
            password_hash=hash_password("Pass1!"),
            roles=["ADMIN"],
            is_active=True,
        )
        # ALUMNO user (no tiene estructura:gestionar)
        user_alumno = AuthUser(
            tenant_id=tenant_a.id,
            email="alumno@ep.test",
            password_hash=hash_password("Pass1!"),
            roles=["ALUMNO"],
            is_active=True,
        )
        session.add_all([user_admin, user_alumno])
        await session.flush()

        # RBAC setup
        rol_admin = Rol(tenant_id=tenant_a.id, nombre="ADMIN")
        rol_alumno = Rol(tenant_id=tenant_a.id, nombre="ALUMNO")
        session.add_all([rol_admin, rol_alumno])
        await session.flush()

        p_estructura = Permiso(tenant_id=tenant_a.id, nombre="estructura:gestionar")
        p_avisos = Permiso(tenant_id=tenant_a.id, nombre="avisos:confirmar")
        session.add_all([p_estructura, p_avisos])
        await session.flush()

        rp_admin = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_admin.id, permiso_id=p_estructura.id)
        rp_alumno = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_alumno.id, permiso_id=p_avisos.id)
        session.add_all([rp_admin, rp_alumno])
        await session.commit()

        token_admin = create_access_token(
            user_id=str(user_admin.id),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
        )
        token_alumno = create_access_token(
            user_id=str(user_alumno.id),
            tenant_id=str(tenant_a.id),
            roles=["ALUMNO"],
        )
        token_tenant_b = create_access_token(
            user_id=str(user_admin.id),
            tenant_id=str(tenant_b.id),
            roles=["ADMIN"],
        )

        app = FastAPI()
        app.include_router(estructura_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield client, token_admin, token_alumno, token_tenant_b, tenant_a.id, tenant_b.id


# ---------------------------------------------------------------------------
# Carreras
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_carrera_sin_permiso_recibe_403(estructura_app):
    """Usuario sin estructura:gestionar recibe 403."""
    client, _, token_alumno, *_ = estructura_app

    r = await client.get("/api/admin/carreras", headers={"Authorization": f"Bearer {token_alumno}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_crear_carrera_devuelve_201_con_datos(estructura_app):
    """POST /api/admin/carreras con permiso crea la carrera y devuelve 201."""
    client, token_admin, *_ = estructura_app

    r = await client.post(
        "/api/admin/carreras",
        json={"codigo": "TUPAD", "nombre": "Tecnicatura UP A Distancia"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["codigo"] == "TUPAD"
    assert "id" in data


@pytest.mark.asyncio
async def test_listar_carreras_devuelve_solo_del_tenant(estructura_app):
    """GET /api/admin/carreras devuelve solo las del tenant del token."""
    client, token_admin, *_ = estructura_app

    await client.post(
        "/api/admin/carreras",
        json={"codigo": "C1", "nombre": "Carrera 1"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    r = await client.get("/api/admin/carreras", headers={"Authorization": f"Bearer {token_admin}"})
    assert r.status_code == 200
    carreras = r.json()
    assert isinstance(carreras, list)
    assert any(c["codigo"] == "C1" for c in carreras)


@pytest.mark.asyncio
async def test_get_carrera_de_otro_tenant_devuelve_404(estructura_app):
    """GET de una carrera perteneciente a otro tenant devuelve 404."""
    client, token_admin, _, _token_b, tenant_a_id, tenant_b_id = estructura_app

    # Insertamos la carrera de tenant_b directamente via service (sin pasar por RBAC)
    from app.core.database import get_session_factory
    from app.services.estructura import EstructuraService

    sf = get_session_factory()
    async with sf() as session:
        svc_b = EstructuraService(session=session, tenant_id=tenant_b_id)
        carrera_b = await svc_b.crear_carrera(codigo="XB", nombre="Carrera Tenant B")
        await session.commit()
        carrera_id = str(carrera_b.id)

    r_get = await client.get(
        f"/api/admin/carreras/{carrera_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r_get.status_code == 404


@pytest.mark.asyncio
async def test_crear_carrera_duplicada_devuelve_409(estructura_app):
    """POST con código duplicado devuelve 409 Conflict."""
    client, token_admin, *_ = estructura_app

    await client.post(
        "/api/admin/carreras",
        json={"codigo": "DUP", "nombre": "Primera"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    r = await client.post(
        "/api/admin/carreras",
        json={"codigo": "DUP", "nombre": "Duplicada"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_carrera_hace_soft_delete(estructura_app):
    """DELETE hace soft delete — la carrera no aparece en el listado posterior."""
    client, token_admin, *_ = estructura_app

    r_create = await client.post(
        "/api/admin/carreras",
        json={"codigo": "DEL", "nombre": "Borrable"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    carrera_id = r_create.json()["id"]

    r_del = await client.delete(
        f"/api/admin/carreras/{carrera_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r_del.status_code == 204

    r_list = await client.get("/api/admin/carreras", headers={"Authorization": f"Bearer {token_admin}"})
    ids = [c["id"] for c in r_list.json()]
    assert carrera_id not in ids


# ---------------------------------------------------------------------------
# Cohortes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_cohorte_activa_en_carrera_inactiva_devuelve_422(estructura_app):
    """POST /api/admin/cohortes con carrera inactiva devuelve 422."""
    client, token_admin, *_ = estructura_app

    r_c = await client.post(
        "/api/admin/carreras",
        json={"codigo": "INA", "nombre": "Inactiva"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    carrera_id = r_c.json()["id"]

    await client.patch(
        f"/api/admin/carreras/{carrera_id}",
        json={"estado": "Inactiva"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    r = await client.post(
        "/api/admin/cohortes",
        json={"carrera_id": carrera_id, "nombre": "MAR-2026", "anio": 2026, "vig_desde": "2026-03-01"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_listar_cohortes_por_carrera_id(estructura_app):
    """GET /api/admin/cohortes?carrera_id filtra correctamente."""
    client, token_admin, *_ = estructura_app

    r_c = await client.post(
        "/api/admin/carreras",
        json={"codigo": "CFIL", "nombre": "Con Filtro"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    carrera_id = r_c.json()["id"]

    await client.post(
        "/api/admin/cohortes",
        json={"carrera_id": carrera_id, "nombre": "AGO-2025", "anio": 2025, "vig_desde": "2025-08-01"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    r = await client.get(
        f"/api/admin/cohortes?carrera_id={carrera_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    cohortes = r.json()
    assert all(c["carrera_id"] == carrera_id for c in cohortes)


# ---------------------------------------------------------------------------
# Materias
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_materias_por_estado(estructura_app):
    """GET /api/admin/materias?estado=Activa devuelve solo activas."""
    client, token_admin, *_ = estructura_app

    await client.post(
        "/api/admin/materias",
        json={"codigo": "ACT_M", "nombre": "Activa"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    r_ina = await client.post(
        "/api/admin/materias",
        json={"codigo": "INA_M", "nombre": "Inactiva"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    ina_id = r_ina.json()["id"]
    await client.patch(
        f"/api/admin/materias/{ina_id}",
        json={"estado": "Inactiva"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    r = await client.get(
        "/api/admin/materias?estado=Activa",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    codigos = [m["codigo"] for m in r.json()]
    assert "ACT_M" in codigos
    assert "INA_M" not in codigos


@pytest.mark.asyncio
async def test_crear_materia_duplicada_devuelve_409(estructura_app):
    """POST con código duplicado en materias devuelve 409."""
    client, token_admin, *_ = estructura_app

    await client.post(
        "/api/admin/materias",
        json={"codigo": "DUP_M2", "nombre": "Primera"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    r = await client.post(
        "/api/admin/materias",
        json={"codigo": "DUP_M2", "nombre": "Duplicada"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_materia_de_otro_tenant_devuelve_404(estructura_app):
    """GET de materia de otro tenant devuelve 404."""
    client, token_admin, _, _token_b, tenant_a_id, tenant_b_id = estructura_app

    from app.core.database import get_session_factory
    from app.services.estructura import EstructuraService

    sf = get_session_factory()
    async with sf() as session:
        svc_b = EstructuraService(session=session, tenant_id=tenant_b_id)
        materia_b = await svc_b.crear_materia(codigo="MB_X", nombre="Materia B")
        await session.commit()
        materia_id = str(materia_b.id)

    r_get = await client.get(
        f"/api/admin/materias/{materia_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r_get.status_code == 404
