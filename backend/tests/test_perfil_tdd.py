"""Tests for C-20: GET /api/perfil y PATCH /api/perfil (tasks 7.1)."""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, encrypt_value, hash_password
from app.models import AuthUser, Tenant, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ctx(valid_env):
    from app.api.v1.routers.perfil import router as perfil_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant Perfil A", slug="perfil-a")
        tenant_b = Tenant(name="Tenant Perfil B", slug="perfil-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_a = AuthUser(
            tenant_id=tenant_a.id,
            email="user-a@perfil.local",
            password_hash=hash_password("P1!"),
            roles=["COORDINADOR"],
        )
        auth_b = AuthUser(
            tenant_id=tenant_b.id,
            email="user-b@perfil.local",
            password_hash=hash_password("P1!"),
            roles=["COORDINADOR"],
        )
        auth_no_usuario = AuthUser(
            tenant_id=tenant_a.id,
            email="ghost@perfil.local",
            password_hash=hash_password("P1!"),
            roles=["COORDINADOR"],
        )
        session.add_all([auth_a, auth_b, auth_no_usuario])
        await session.flush()

        usuario_a = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=auth_a.id,
            nombre="Juan",
            apellidos="Perez",
            email_encrypted=encrypt_value("user-a@perfil.local"),
            email_hash="hash-a",
            cuil_encrypted=encrypt_value("20-12345678-9"),
            cbu_encrypted=encrypt_value("0000000000000000000000"),
            banco="Banco Nación",
        )
        usuario_b = Usuario(
            tenant_id=tenant_b.id,
            auth_user_id=auth_b.id,
            nombre="Maria",
            apellidos="Lopez",
            email_encrypted=encrypt_value("user-b@perfil.local"),
            email_hash="hash-b",
        )
        session.add_all([usuario_a, usuario_b])
        await session.commit()

    def _tok(auth_user_id, tenant_id, roles):
        return create_access_token(
            user_id=str(auth_user_id), tenant_id=str(tenant_id), roles=roles
        )

    app = FastAPI()
    app.include_router(perfil_router)

    return {
        "app": app,
        "usuario_a": usuario_a,
        "tok_a": _tok(auth_a.id, tenant_a.id, ["COORDINADOR"]),
        "tok_b": _tok(auth_b.id, tenant_b.id, ["COORDINADOR"]),
        "tok_no_usuario": _tok(auth_no_usuario.id, tenant_a.id, ["COORDINADOR"]),
    }


# ---------------------------------------------------------------------------
# Task 7.1 — GET /api/perfil
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_perfil_retorna_pii_en_claro(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.get("/api/perfil", headers=_auth(ctx["tok_a"]))
    assert r.status_code == 200
    body = r.json()
    assert body["nombre"] == "Juan"
    assert body["apellidos"] == "Perez"
    assert body["email"] == "user-a@perfil.local"
    assert body["cuil"] == "20-12345678-9"
    assert body["cbu"] == "0000000000000000000000"
    assert body["banco"] == "Banco Nación"


@pytest.mark.asyncio
async def test_get_perfil_sin_usuario_retorna_404(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.get("/api/perfil", headers=_auth(ctx["tok_no_usuario"]))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_perfil_sin_auth_retorna_401(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.get("/api/perfil")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Task 7.1 — PATCH /api/perfil
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_perfil_actualiza_banco_y_cbu(ctx):
    payload = {"banco": "BBVA", "cbu": "9999999999999999999999"}
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.patch("/api/perfil", json=payload, headers=_auth(ctx["tok_a"]))
    assert r.status_code == 200
    body = r.json()
    assert body["banco"] == "BBVA"
    assert body["cbu"] == "9999999999999999999999"
    assert body["nombre"] == "Juan"


@pytest.mark.asyncio
async def test_patch_perfil_cuil_no_se_modifica(ctx):
    # cuil is not in PerfilUpdateRequest → Pydantic rejects with 422
    payload = {"cuil": "99-99999999-9"}
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.patch("/api/perfil", json=payload, headers=_auth(ctx["tok_a"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_perfil_solo_campos_enviados_se_modifican(ctx):
    payload = {"nombre": "Giovanni"}
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.patch("/api/perfil", json=payload, headers=_auth(ctx["tok_a"]))
    assert r.status_code == 200
    body = r.json()
    assert body["nombre"] == "Giovanni"
    assert body["apellidos"] == "Perez"
    assert body["banco"] == "Banco Nación"
