"""Tests for C-15: crear aviso, vigencia y audiencia (tasks 6.1–6.3)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import (
    AuditLog,
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

        tenant_a = Tenant(name="Tenant AvisoA", slug="aviso-a")
        tenant_b = Tenant(name="Tenant AvisoB", slug="aviso-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@aviso-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_alumno1 = AuthUser(
            id=alumno1_uuid, tenant_id=tenant_a.id,
            email="alumno1@aviso-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_alumno2 = AuthUser(
            id=alumno2_uuid, tenant_id=tenant_a.id,
            email="alumno2@aviso-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@aviso-b.local",
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

        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CRR-A", nombre="Carrera A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRR-B", nombre="Carrera B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera_a.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-A", nombre="Materia A")
        cohorte_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=carrera_b.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
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
        session.add_all([usuario_coord, usuario_alumno1, usuario_alumno2])
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
        ])
        await session.commit()

    app = FastAPI()
    app.include_router(avisos_router)

    def _tok(uid, tid, roles):
        return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)

    return {
        "app": app,
        "tenant_a": tenant_a,
        "materia_a": materia_a,
        "cohorte_a": cohorte_a,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_alumno1": _tok(alumno1_uuid, tenant_a.id, ["ALUMNO"]),
        "tok_alumno2": _tok(alumno2_uuid, tenant_a.id, ["ALUMNO"]),
    }


# ---------------------------------------------------------------------------
# Task 6.1 — Crear aviso
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_aviso_global_exitoso(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json=_aviso_payload(), headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 201
    body = r.json()
    assert body["titulo"] == "Aviso test"
    assert body["alcance"] == "Global"
    assert body["acusado"] is False


@pytest.mark.asyncio
async def test_crear_aviso_sin_permiso_retorna_403(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json=_aviso_payload(), headers=_auth(ctx["tok_alumno1"]))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_crear_aviso_fin_anterior_a_inicio_retorna_422(ctx):
    payload = _aviso_payload(inicio_en=_utc(2).isoformat(), fin_en=_utc(1).isoformat())
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_aviso_campo_extra_retorna_422(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json={**_aviso_payload(), "campo_fantasma": "nope"}, headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_aviso_por_materia(ctx):
    payload = _aviso_payload(alcance="PorMateria", materia_id=str(ctx["materia_a"].id))
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 201
    assert r.json()["alcance"] == "PorMateria"


@pytest.mark.asyncio
async def test_crear_aviso_por_rol(ctx):
    payload = _aviso_payload(alcance="PorRol", rol_destino="ALUMNO")
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 201
    assert r.json()["rol_destino"] == "ALUMNO"


@pytest.mark.asyncio
async def test_crear_aviso_genera_audit(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        r = await c.post("/api/avisos", json=_aviso_payload(titulo="Audit Test"), headers=_auth(ctx["tok_coord"]))
    assert r.status_code == 201
    aviso_id = r.json()["id"]
    async with get_session_factory()() as s:
        from sqlalchemy import select
        log = await s.scalar(
            select(AuditLog)
            .where(AuditLog.accion == "AVISO_CREAR")
            .where(AuditLog.tenant_id == ctx["tenant_a"].id)
        )
    assert log is not None
    assert str(aviso_id) in str(log.detalle)


# ---------------------------------------------------------------------------
# Task 6.2 — Filtrado por vigencia (RN-18)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aviso_dentro_ventana_aparece(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=_aviso_payload(titulo="Vigente"), headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
    assert any(a["titulo"] == "Vigente" for a in r.json())


@pytest.mark.asyncio
async def test_aviso_inicio_futuro_no_aparece(ctx):
    payload = _aviso_payload(titulo="Futuro", inicio_en=_utc(2).isoformat(), fin_en=_utc(4).isoformat())
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
    assert all(a["titulo"] != "Futuro" for a in r.json())


@pytest.mark.asyncio
async def test_aviso_vencido_no_aparece(ctx):
    payload = _aviso_payload(titulo="Vencido", inicio_en=_utc(-4).isoformat(), fin_en=_utc(-2).isoformat())
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
    assert all(a["titulo"] != "Vencido" for a in r.json())


# ---------------------------------------------------------------------------
# Task 6.3 — Filtrado por audiencia (RN-20)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aviso_global_visible_para_cualquier_rol(ctx):
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=_aviso_payload(titulo="Global"), headers=_auth(ctx["tok_coord"]))
        r1 = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
        r2 = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno2"]))
    assert any(a["titulo"] == "Global" for a in r1.json())
    assert any(a["titulo"] == "Global" for a in r2.json())


@pytest.mark.asyncio
async def test_aviso_por_rol_solo_para_ese_rol(ctx):
    payload = _aviso_payload(alcance="PorRol", rol_destino="COORDINADOR", titulo="Solo Coord")
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
    assert all(a["titulo"] != "Solo Coord" for a in r.json())


@pytest.mark.asyncio
async def test_aviso_por_materia_solo_para_matriculados(ctx):
    payload = _aviso_payload(
        alcance="PorMateria", materia_id=str(ctx["materia_a"].id), titulo="Solo Materia"
    )
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r_in = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
        r_out = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno2"]))
    assert any(a["titulo"] == "Solo Materia" for a in r_in.json())
    assert all(a["titulo"] != "Solo Materia" for a in r_out.json())


@pytest.mark.asyncio
async def test_aviso_por_cohorte_solo_para_cohorte(ctx):
    payload = _aviso_payload(
        alcance="PorCohorte", cohorte_id=str(ctx["cohorte_a"].id), titulo="Solo Cohorte"
    )
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as c:
        await c.post("/api/avisos", json=payload, headers=_auth(ctx["tok_coord"]))
        r_in = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno1"]))
        r_out = await c.get("/api/avisos", headers=_auth(ctx["tok_alumno2"]))
    assert any(a["titulo"] == "Solo Cohorte" for a in r_in.json())
    assert all(a["titulo"] != "Solo Cohorte" for a in r_out.json())
