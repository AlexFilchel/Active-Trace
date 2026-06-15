"""C-18 Task 7.1 — CRUD SalarioBase y SalarioPlus, vigencia, permisos, isolamiento."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Permiso, Rol, RolPermiso, Tenant
from tests.usuarios_test_utils import clean_database, ensure_schema


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def ctx(valid_env):
    from app.api.v1.routers.salarios import router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as s:
        await clean_database(s)

        tenant_a = Tenant(name="Sal A", slug="sal-a")
        tenant_b = Tenant(name="Sal B", slug="sal-b")
        s.add_all([tenant_a, tenant_b])
        await s.flush()

        finanzas_auth = AuthUser(
            tenant_id=tenant_a.id, email="fin@sal-a.local",
            password_hash=hash_password("P1!"), roles=["FINANZAS"],
        )
        noperm_auth = AuthUser(
            tenant_id=tenant_a.id, email="nop@sal-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        finanzas_b = AuthUser(
            tenant_id=tenant_b.id, email="fin@sal-b.local",
            password_hash=hash_password("P1!"), roles=["FINANZAS"],
        )
        s.add_all([finanzas_auth, noperm_auth, finanzas_b])
        await s.flush()

        rol_fin_a = Rol(tenant_id=tenant_a.id, nombre="FINANZAS")
        rol_fin_b = Rol(tenant_id=tenant_b.id, nombre="FINANZAS")
        s.add_all([rol_fin_a, rol_fin_b])
        await s.flush()

        perm_a = Permiso(tenant_id=tenant_a.id, nombre="liquidaciones:configurar-salarios")
        perm_b = Permiso(tenant_id=tenant_b.id, nombre="liquidaciones:configurar-salarios")
        s.add_all([perm_a, perm_b])
        await s.flush()
        s.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_fin_a.id, permiso_id=perm_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_fin_b.id, permiso_id=perm_b.id),
        ])
        await s.commit()

    fin_id = finanzas_auth.id
    fin_b_id = finanzas_b.id
    nop_id = noperm_auth.id

    app = FastAPI()
    app.include_router(router)

    return {
        "app": app,
        "tok_fin": _tok(fin_id, tenant_a.id, ["FINANZAS"]),
        "tok_fin_b": _tok(fin_b_id, tenant_b.id, ["FINANZAS"]),
        "tok_noperm": _tok(nop_id, tenant_a.id, ["ALUMNO"]),
    }


_BASE_PAYLOAD = {
    "rol": "PROFESOR",
    "monto": "5000.00",
    "desde": "2026-01-01",
    "hasta": None,
}

_PLUS_PAYLOAD = {
    "grupo": "PROG",
    "rol": "PROFESOR",
    "descripcion": "Plus programación",
    "monto": "800.00",
    "desde": "2026-01-01",
    "hasta": None,
}


# ---------------------------------------------------------------------------
# RED → GREEN: salario base CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_salario_base_201(ctx):
    """RED→GREEN: POST /api/salarios/base → 201 con campos correctos."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/salarios/base", json=_BASE_PAYLOAD, headers=_auth(c["tok_fin"]))
    assert r.status_code == 201
    body = r.json()
    assert body["rol"] == "PROFESOR"
    assert body["monto"] == "5000.00"
    assert body["hasta"] is None


@pytest.mark.asyncio
async def test_salario_base_sin_permiso_403(ctx):
    """Sin liquidaciones:configurar-salarios → 403."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/salarios/base", json=_BASE_PAYLOAD, headers=_auth(c["tok_noperm"]))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_salario_plus_201(ctx):
    """TRIANGULATE: POST /api/salarios/plus → 201."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/salarios/plus", json=_PLUS_PAYLOAD, headers=_auth(c["tok_fin"]))
    assert r.status_code == 201
    body = r.json()
    assert body["grupo"] == "PROG"
    assert body["monto"] == "800.00"


@pytest.mark.asyncio
async def test_listar_salarios_base_filtro_rol(ctx):
    """TRIANGULATE: listar filtrando por rol retorna solo ese rol."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post("/api/salarios/base", json=_BASE_PAYLOAD, headers=_auth(c["tok_fin"]))
        await cli.post(
            "/api/salarios/base",
            json={**_BASE_PAYLOAD, "rol": "TUTOR", "monto": "3000.00"},
            headers=_auth(c["tok_fin"]),
        )
        r = await cli.get("/api/salarios/base", params={"rol": "PROFESOR"}, headers=_auth(c["tok_fin"]))
    assert r.status_code == 200
    data = r.json()
    assert all(item["rol"] == "PROFESOR" for item in data)


@pytest.mark.asyncio
async def test_aislamiento_tenant_salarios(ctx):
    """TRIANGULATE: Tenant B no ve salarios de Tenant A."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post("/api/salarios/base", json=_BASE_PAYLOAD, headers=_auth(c["tok_fin"]))
        r_b = await cli.get("/api/salarios/base", headers=_auth(c["tok_fin_b"]))
    assert r_b.status_code == 200
    assert r_b.json() == []
