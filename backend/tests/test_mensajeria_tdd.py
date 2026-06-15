"""Tests for C-20: inbox endpoints (tasks 7.2)."""
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
    from app.api.v1.routers.inbox import router as inbox_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant Msg A", slug="msg-a")
        tenant_b = Tenant(name="Tenant Msg B", slug="msg-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_alice = AuthUser(
            tenant_id=tenant_a.id,
            email="alice@msg-a.local",
            password_hash=hash_password("P1!"),
            roles=["COORDINADOR"],
        )
        auth_bob = AuthUser(
            tenant_id=tenant_a.id,
            email="bob@msg-a.local",
            password_hash=hash_password("P1!"),
            roles=["COORDINADOR"],
        )
        auth_other_tenant = AuthUser(
            tenant_id=tenant_b.id,
            email="carol@msg-b.local",
            password_hash=hash_password("P1!"),
            roles=["COORDINADOR"],
        )
        session.add_all([auth_alice, auth_bob, auth_other_tenant])
        await session.flush()

        usuario_alice = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=auth_alice.id,
            nombre="Alice",
            apellidos="A",
            email_encrypted=encrypt_value("alice@msg-a.local"),
            email_hash="hash-alice",
        )
        usuario_bob = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=auth_bob.id,
            nombre="Bob",
            apellidos="B",
            email_encrypted=encrypt_value("bob@msg-a.local"),
            email_hash="hash-bob",
        )
        usuario_carol = Usuario(
            tenant_id=tenant_b.id,
            auth_user_id=auth_other_tenant.id,
            nombre="Carol",
            apellidos="C",
            email_encrypted=encrypt_value("carol@msg-b.local"),
            email_hash="hash-carol",
        )
        session.add_all([usuario_alice, usuario_bob, usuario_carol])
        await session.commit()

    def _tok(auth_user_id, tenant_id, roles):
        return create_access_token(
            user_id=str(auth_user_id), tenant_id=str(tenant_id), roles=roles
        )

    app = FastAPI()
    app.include_router(inbox_router)

    return {
        "app": app,
        "usuario_alice": usuario_alice,
        "usuario_bob": usuario_bob,
        "usuario_carol": usuario_carol,
        "tok_alice": _tok(auth_alice.id, tenant_a.id, ["COORDINADOR"]),
        "tok_bob": _tok(auth_bob.id, tenant_a.id, ["COORDINADOR"]),
        "tok_carol": _tok(auth_other_tenant.id, tenant_b.id, ["COORDINADOR"]),
    }


# ---------------------------------------------------------------------------
# Task 7.2 — crear hilo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_hilo_exitoso(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_bob"].id),
        "asunto": "Hola Bob",
        "cuerpo": "Este es el primer mensaje",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
    assert r.status_code == 201
    body = r.json()
    assert body["asunto"] == "Hola Bob"
    assert "id" in body


@pytest.mark.asyncio
async def test_crear_hilo_destinatario_otro_tenant_retorna_404(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_carol"].id),  # tenant_b usuario
        "asunto": "Hola Carol",
        "cuerpo": "Este mensaje no debería llegar",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_hilo_self_message_retorna_422(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_alice"].id),  # same as sender
        "asunto": "Mensaje a mi mismo",
        "cuerpo": "Esto no va",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Task 7.2 — listar hilos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_hilos_solo_los_propios(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_bob"].id),
        "asunto": "Para Bob",
        "cuerpo": "Contenido",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
        r_bob = await c.get("/api/inbox/hilos", headers=_auth(ctx["tok_bob"]))
        r_alice = await c.get("/api/inbox/hilos", headers=_auth(ctx["tok_alice"]))
    # Bob received → appears in Bob's inbox
    assert r_bob.status_code == 200
    assert len(r_bob.json()) == 1
    # Alice sent but is not the destinatario → doesn't appear in Alice's inbox
    assert r_alice.status_code == 200
    assert len(r_alice.json()) == 0


# ---------------------------------------------------------------------------
# Task 7.2 — leer mensajes y marcar leído
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_leer_mensajes_marca_leido(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_bob"].id),
        "asunto": "Leeme",
        "cuerpo": "Este mensaje va a ser leído",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r_crear = await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
        hilo_id = r_crear.json()["id"]

        # Bob reads messages → marks as read
        r_mensajes = await c.get(
            f"/api/inbox/hilos/{hilo_id}/mensajes", headers=_auth(ctx["tok_bob"])
        )
        assert r_mensajes.status_code == 200
        mensajes = r_mensajes.json()
        assert len(mensajes) == 1
        assert mensajes[0]["leido"] is False  # initially not read (snapshot before commit)

        # Check inbox again — no_leidos should be 0 now
        r_inbox = await c.get("/api/inbox/hilos", headers=_auth(ctx["tok_bob"]))
        assert r_inbox.json()[0]["mensajes_no_leidos"] == 0


# ---------------------------------------------------------------------------
# Task 7.2 — responder
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_responder_hilo_exitoso(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_bob"].id),
        "asunto": "Hilo para responder",
        "cuerpo": "Primer mensaje",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r_hilo = await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
        hilo_id = r_hilo.json()["id"]

        r_respuesta = await c.post(
            f"/api/inbox/hilos/{hilo_id}/mensajes",
            json={"destinatario_id": str(ctx["usuario_alice"].id), "cuerpo": "Respuesta de Bob"},
            headers=_auth(ctx["tok_bob"]),
        )
    assert r_respuesta.status_code == 201
    assert r_respuesta.json()["cuerpo"] == "Respuesta de Bob"


@pytest.mark.asyncio
async def test_no_participante_no_puede_leer_mensajes(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_bob"].id),
        "asunto": "Privado",
        "cuerpo": "Solo Alice y Bob",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r_hilo = await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
        hilo_id = r_hilo.json()["id"]

        # Carol (different tenant) tries to read → 404 because hilo doesn't exist in her tenant
        r_carol = await c.get(
            f"/api/inbox/hilos/{hilo_id}/mensajes", headers=_auth(ctx["tok_carol"])
        )
    assert r_carol.status_code == 404


@pytest.mark.asyncio
async def test_aislamiento_tenant_en_listar(ctx):
    payload = {
        "destinatario_id": str(ctx["usuario_bob"].id),
        "asunto": "Solo tenant A",
        "cuerpo": "Mensaje interno de tenant A",
    }
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/inbox/hilos", json=payload, headers=_auth(ctx["tok_alice"]))
        r_carol = await c.get("/api/inbox/hilos", headers=_auth(ctx["tok_carol"]))
    assert r_carol.status_code == 200
    assert r_carol.json() == []
