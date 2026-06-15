"""C-18 Task 7.4 — Facturas: crear, 422 no-facturador, abonar, listar, aislamiento."""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Permiso, Rol, RolPermiso, Tenant
from app.models.usuarios import Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def ctx(valid_env):
    from app.api.v1.routers.facturas import router as facturas_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as s:
        await clean_database(s)

        tenant_a = Tenant(name="Fact A", slug="fact-a")
        tenant_b = Tenant(name="Fact B", slug="fact-b")
        s.add_all([tenant_a, tenant_b])
        await s.flush()

        auth_fin_a = AuthUser(
            tenant_id=tenant_a.id, email="fin@fact-a.local",
            password_hash=hash_password("P1!"), roles=["FINANZAS"],
        )
        auth_fin_b = AuthUser(
            tenant_id=tenant_b.id, email="fin@fact-b.local",
            password_hash=hash_password("P1!"), roles=["FINANZAS"],
        )
        s.add_all([auth_fin_a, auth_fin_b])
        await s.flush()

        rol_fin_a = Rol(tenant_id=tenant_a.id, nombre="FINANZAS")
        rol_fin_b = Rol(tenant_id=tenant_b.id, nombre="FINANZAS")
        s.add_all([rol_fin_a, rol_fin_b])
        await s.flush()

        perm_a = Permiso(tenant_id=tenant_a.id, nombre="liquidaciones:gestionar-facturas")
        perm_b = Permiso(tenant_id=tenant_b.id, nombre="liquidaciones:gestionar-facturas")
        s.add_all([perm_a, perm_b])
        await s.flush()
        s.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_fin_a.id, permiso_id=perm_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_fin_b.id, permiso_id=perm_b.id),
        ])

        usuario_facturador = Usuario(
            tenant_id=tenant_a.id, nombre="Fact", apellidos="A",
            email_encrypted="enc-fact-a", email_hash="hash-fact-a", facturador=True,
        )
        usuario_no_facturador = Usuario(
            tenant_id=tenant_a.id, nombre="NoFact", apellidos="A",
            email_encrypted="enc-nofact-a", email_hash="hash-nofact-a", facturador=False,
        )
        s.add_all([usuario_facturador, usuario_no_facturador])
        await s.flush()
        await s.commit()

    app = FastAPI()
    app.include_router(facturas_router)

    return {
        "app": app,
        "tok_fin_a": _tok(auth_fin_a.id, tenant_a.id, ["FINANZAS"]),
        "tok_fin_b": _tok(auth_fin_b.id, tenant_b.id, ["FINANZAS"]),
        "usuario_facturador_id": str(usuario_facturador.id),
        "usuario_no_facturador_id": str(usuario_no_facturador.id),
    }


_PERIODO = "2026-01"


def _payload(usuario_id: str) -> dict:
    return {
        "usuario_id": usuario_id,
        "periodo": _PERIODO,
        "detalle": "Servicios enero",
        "referencia_archivo": "factura.pdf",
        "tamano_kb": "512.00",
    }


# ---------------------------------------------------------------------------
# RED → GREEN: crear factura para usuario facturador
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_factura_facturador_201(ctx):
    """RED→GREEN: POST /api/facturas para facturador → 201."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/facturas",
            json=_payload(c["usuario_facturador_id"]),
            headers=_auth(c["tok_fin_a"]),
        )
    assert r.status_code == 201
    body = r.json()
    assert body["estado"] == "Pendiente"
    assert body["abonada_at"] is None
    assert body["periodo"] == _PERIODO


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_factura_no_facturador_422(ctx):
    """TRIANGULATE: usuario sin facturador=True → 422."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/facturas",
            json=_payload(c["usuario_no_facturador_id"]),
            headers=_auth(c["tok_fin_a"]),
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_abonar_factura_cambia_estado_y_setea_fecha(ctx):
    """TRIANGULATE: PATCH /abonar → estado=Abonada, abonada_at != None."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        cr = await cli.post(
            "/api/facturas",
            json=_payload(c["usuario_facturador_id"]),
            headers=_auth(c["tok_fin_a"]),
        )
        factura_id = cr.json()["id"]
        r = await cli.patch(f"/api/facturas/{factura_id}/abonar", headers=_auth(c["tok_fin_a"]))

    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "Abonada"
    assert body["abonada_at"] is not None


@pytest.mark.asyncio
async def test_listar_facturas_filtra_por_estado(ctx):
    """TRIANGULATE: listar con ?estado=Abonada retorna solo las abonadas."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        cr1 = await cli.post("/api/facturas", json=_payload(c["usuario_facturador_id"]), headers=_auth(c["tok_fin_a"]))
        cr2 = await cli.post("/api/facturas", json=_payload(c["usuario_facturador_id"]), headers=_auth(c["tok_fin_a"]))
        fid1 = cr1.json()["id"]
        await cli.patch(f"/api/facturas/{fid1}/abonar", headers=_auth(c["tok_fin_a"]))

        r = await cli.get("/api/facturas", params={"estado": "Abonada"}, headers=_auth(c["tok_fin_a"]))

    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["estado"] == "Abonada"


@pytest.mark.asyncio
async def test_aislamiento_tenant_facturas(ctx):
    """TRIANGULATE: Tenant B no ve facturas de Tenant A."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post("/api/facturas", json=_payload(c["usuario_facturador_id"]), headers=_auth(c["tok_fin_a"]))
        r = await cli.get("/api/facturas", headers=_auth(c["tok_fin_b"]))

    assert r.status_code == 200
    assert r.json() == []
