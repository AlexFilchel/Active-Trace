"""Tests for C-15: ack, gestión, aviso inactivo (tasks 6.4–6.7)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import (
    AuthUser,
    Carrera,
    Cohorte,
    Materia,
    Permiso,
    Rol,
    RolPermiso,
    Tenant,
    Usuario,
)
from app.models.usuarios import Asignacion
from tests.usuarios_test_utils import clean_database, ensure_schema


def _utc(delta_hours: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=delta_hours)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _aviso_payload(**kwargs) -> dict:
    defaults = {
        "alcance": "Global",
        "titulo": "Aviso test",
        "cuerpo": "Cuerpo del aviso de prueba",
        "inicio_en": _utc(-1).isoformat(),
        "fin_en": _utc(1).isoformat(),
    }
    return {**defaults, **kwargs}


@pytest.fixture
async def ctx(valid_env):
    """Two tenants, coordinator, two alumnos. alumno1 enrolled, alumno2 not."""
    from app.api.v1.routers.avisos import router as avisos_router

    await ensure_schema()
    session_factory = get_session_factory()

    alumno1_uuid = uuid.uuid4()
    alumno2_uuid = uuid.uuid4()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant AckA", slug="ack-a")
        tenant_b = Tenant(name="Tenant AckB", slug="ack-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@ack-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_alumno1 = AuthUser(
            id=alumno1_uuid, tenant_id=tenant_a.id,
            email="alumno1@ack-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_alumno2 = AuthUser(
            id=alumno2_uuid, tenant_id=tenant_a.id,
            email="alumno2@ack-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@ack-b.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        session.add_all([auth_coord, auth_alumno1, auth_alumno2, auth_coord_b])
        await session.flush()

        rol_coord = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_alumno = Rol(tenant_id=tenant_a.id, nombre="ALUMNO")
        rol_coord_b = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
        session.add_all([rol_coord, rol_alumno, rol_coord_b])
        await session.flush()

        perm = Permiso(tenant_id=tenant_a.id, nombre="avisos:publicar")
        perm_b = Permiso(tenant_id=tenant_b.id, nombre="avisos:publicar")
        session.add_all([perm, perm_b])
        await session.flush()
        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=perm.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_coord_b.id, permiso_id=perm_b.id),
        ])

        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CRA", nombre="Carrera A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRB", nombre="Carrera B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera_a.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MATA", nombre="Materia A")
        cohorte_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=carrera_b.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MATB", nombre="Materia B")
        session.add_all([cohorte_a, materia_a, cohorte_b, materia_b])
        await session.flush()

        usuario_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="A",
            email_encrypted="enc-coord-a", email_hash="hash-coord-a",
        )
        usuario_alumno1 = Usuario(
            id=alumno1_uuid, tenant_id=tenant_a.id, auth_user_id=auth_alumno1.id,
            nombre="Alumno", apellidos="Uno",
            email_encrypted="enc-alum1-a", email_hash="hash-alum1-a",
        )
        usuario_alumno2 = Usuario(
            id=alumno2_uuid, tenant_id=tenant_a.id, auth_user_id=auth_alumno2.id,
            nombre="Alumno", apellidos="Dos",
            email_encrypted="enc-alum2-a", email_hash="hash-alum2-a",
        )
        usuario_coord_b = Usuario(
            tenant_id=tenant_b.id, auth_user_id=auth_coord_b.id,
            nombre="Coord", apellidos="B",
            email_encrypted="enc-coord-b", email_hash="hash-coord-b",
        )
        session.add_all([usuario_coord, usuario_alumno1, usuario_alumno2, usuario_coord_b])
        await session.flush()

        session.add_all([
            Asignacion(
                tenant_id=tenant_a.id,
                usuario_id=usuario_coord.id, rol_id=rol_coord.id,
                materia_id=materia_a.id, carrera_id=carrera_a.id,
                cohorte_id=cohorte_a.id, desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_a.id,
                usuario_id=usuario_alumno1.id, rol_id=rol_alumno.id,
                materia_id=materia_a.id, carrera_id=carrera_a.id,
                cohorte_id=cohorte_a.id, desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_b.id,
                usuario_id=usuario_coord_b.id, rol_id=rol_coord_b.id,
                materia_id=materia_b.id, carrera_id=carrera_b.id,
                cohorte_id=cohorte_b.id, desde=date(2026, 1, 1),
            ),
        ])
        await session.commit()

    app = FastAPI()
    app.include_router(avisos_router)

    def _tok(uid, tid, roles):
        return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)

    return {
        "app": app,
        "tenant_a": tenant_a,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_alumno1": _tok(alumno1_uuid, tenant_a.id, ["ALUMNO"]),
        "tok_alumno2": _tok(alumno2_uuid, tenant_a.id, ["ALUMNO"]),
        "tok_coord_b": _tok(auth_coord_b.id, tenant_b.id, ["COORDINADOR"]),
    }


# ---------------------------------------------------------------------------
# Task 6.4 — Ack (RN-19)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ack_crea_acknowledgment(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=_aviso_payload(requiere_ack=True), headers=_auth(ctx["tok_coord"]))
        aviso_id = cr.json()["id"]
        r = await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
    assert r.status_code == 201
    body = r.json()
    assert body["ya_existia"] is False
    assert body["aviso_id"] == aviso_id


@pytest.mark.asyncio
async def test_ack_idempotente_retorna_200(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=_aviso_payload(requiere_ack=True), headers=_auth(ctx["tok_coord"]))
        aviso_id = cr.json()["id"]
        await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
        r2 = await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
    assert r2.status_code == 200
    assert r2.json()["ya_existia"] is True


@pytest.mark.asyncio
async def test_aviso_acusado_no_aparece_en_listado(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post(
            "/api/avisos",
            json=_aviso_payload(titulo="Para Ack", requiere_ack=True),
            headers=_auth(ctx["tok_coord"]),
        )
        aviso_id = cr.json()["id"]
        await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
        r = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
    assert all(a["id"] != aviso_id for a in r.json())


@pytest.mark.asyncio
async def test_incluir_acusados_muestra_con_flag(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post(
            "/api/avisos",
            json=_aviso_payload(titulo="Para Ack 2", requiere_ack=True),
            headers=_auth(ctx["tok_coord"]),
        )
        aviso_id = cr.json()["id"]
        await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
        r = await c.get("/api/avisos?incluir_acusados=true", headers=_auth(ctx["tok_alumno1"]))
    match = next((a for a in r.json() if a["id"] == aviso_id), None)
    assert match is not None
    assert match["acusado"] is True


# ---------------------------------------------------------------------------
# Task 6.5 — Ack inválido
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ack_en_aviso_sin_requiere_ack_retorna_422(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=_aviso_payload(requiere_ack=False), headers=_auth(ctx["tok_coord"]))
        r = await c.post(f"/api/avisos/{cr.json()['id']}/ack", headers=_auth(ctx["tok_alumno1"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_ack_en_aviso_vencido_retorna_422(ctx):
    payload = _aviso_payload(
        requiere_ack=True,
        inicio_en=_utc(-4).isoformat(),
        fin_en=_utc(-2).isoformat(),
    )
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r = await c.post(f"/api/avisos/{cr.json()['id']}/ack", headers=_auth(ctx["tok_alumno1"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_ack_en_aviso_de_otro_tenant_retorna_404(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=_aviso_payload(requiere_ack=True), headers=_auth(ctx["tok_coord_b"]))
        r = await c.post(f"/api/avisos/{cr.json()['id']}/ack", headers=_auth(ctx["tok_alumno1"]))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Task 6.6 — Gestión
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gestion_retorna_todos_incluyendo_fuera_de_vigencia(ctx):
    vencido = _aviso_payload(titulo="Vencido Gestion", inicio_en=_utc(-4).isoformat(), fin_en=_utc(-2).isoformat())
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=_aviso_payload(titulo="Vigente Gestion"), headers=_auth(ctx["tok_coord"]))
        await c.post("/api/avisos", json=vencido, headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos/gestion", headers=_auth(ctx["tok_coord"]))
    titulos = [a["titulo"] for a in r.json()]
    assert "Vigente Gestion" in titulos
    assert "Vencido Gestion" in titulos


@pytest.mark.asyncio
async def test_gestion_isolada_por_tenant(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=_aviso_payload(titulo="Tenant A Aviso"), headers=_auth(ctx["tok_coord"]))
        r_b = await c.get("/api/avisos/gestion", headers=_auth(ctx["tok_coord_b"]))
    assert all(a["titulo"] != "Tenant A Aviso" for a in r_b.json())


@pytest.mark.asyncio
async def test_patch_aviso_actualiza_campos(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=_aviso_payload(titulo="Original"), headers=_auth(ctx["tok_coord"]))
        aviso_id = cr.json()["id"]
        r = await c.patch(f"/api/avisos/{aviso_id}", json={"titulo": "Actualizado"}, headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 200
    assert r.json()["titulo"] == "Actualizado"


@pytest.mark.asyncio
async def test_metricas_retorna_conteo_correcto(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=_aviso_payload(requiere_ack=True), headers=_auth(ctx["tok_coord"]))
        aviso_id = cr.json()["id"]
        await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
        r = await c.get(f"/api/avisos/{aviso_id}/metricas", headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 200
    assert r.json()["total_acks"] == 1
    assert r.json()["requiere_ack"] is True


@pytest.mark.asyncio
async def test_gestion_incluye_total_acks(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post(
            "/api/avisos",
            json=_aviso_payload(titulo="Con Acks", requiere_ack=True),
            headers=_auth(ctx["tok_coord"]),
        )
        aviso_id = cr.json()["id"]
        await c.post(f"/api/avisos/{aviso_id}/ack", headers=_auth(ctx["tok_alumno1"]))
        r = await c.get("/api/avisos/gestion", headers=_auth(ctx["tok_coord"]))
    match = next((a for a in r.json() if a["id"] == aviso_id), None)
    assert match is not None
    assert match["total_acks"] == 1


# ---------------------------------------------------------------------------
# Task 6.7 — Aviso inactivo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aviso_inactivo_no_aparece_en_listado_usuario(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=_aviso_payload(titulo="Inactivo", activo=False), headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
    assert all(a["titulo"] != "Inactivo" for a in r.json())


@pytest.mark.asyncio
async def test_aviso_inactivo_si_aparece_en_gestion(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=_aviso_payload(titulo="Inactivo Gestion", activo=False), headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos/gestion", headers=_auth(ctx["tok_coord"]))
    assert any(a["titulo"] == "Inactivo Gestion" for a in r.json())


@pytest.mark.asyncio
async def test_aviso_inactivo_no_acepta_ack(ctx):
    payload = _aviso_payload(requiere_ack=True, activo=False)
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        cr = await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r = await c.post(f"/api/avisos/{cr.json()['id']}/ack", headers=_auth(ctx["tok_alumno1"]))
    assert r.status_code == 422
