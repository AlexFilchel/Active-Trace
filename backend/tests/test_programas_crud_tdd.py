"""Tests C-17 — task 6.1: ProgramaMateria CRUD."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

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


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ctx(valid_env):
    """Tenant A: coordinador + sin-permiso. Tenant B: coordinador_b."""
    from app.api.v1.routers.programas import programas_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant ProgramasA", slug="programas-a")
        tenant_b = Tenant(name="Tenant ProgramasB", slug="programas-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@prog-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_noperm = AuthUser(
            tenant_id=tenant_a.id, email="noperm@prog-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@prog-b.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        session.add_all([auth_coord, auth_noperm, auth_coord_b])
        await session.flush()

        rol_coord_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_coord_b = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
        session.add_all([rol_coord_a, rol_coord_b])
        await session.flush()

        perm_a = Permiso(tenant_id=tenant_a.id, nombre="estructura:gestionar")
        perm_b = Permiso(tenant_id=tenant_b.id, nombre="estructura:gestionar")
        session.add_all([perm_a, perm_b])
        await session.flush()
        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord_a.id, permiso_id=perm_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_coord_b.id, permiso_id=perm_b.id),
        ])

        carrera = Carrera(tenant_id=tenant_a.id, codigo="CRR-P", nombre="Carrera Progs")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRR-PB", nombre="Carrera Progs B")
        session.add_all([carrera, carrera_b])
        await session.flush()

        cohorte = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        cohorte_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=carrera_b.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia = Materia(tenant_id=tenant_a.id, codigo="MAT-P", nombre="Materia Progs")
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-PB", nombre="Materia Progs B")
        session.add_all([cohorte, cohorte_b, materia, materia_b])
        await session.flush()

        u_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="P",
            email_encrypted="enc-cp", email_hash="hash-cp",
        )
        session.add(u_coord)
        await session.flush()
        session.add(
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_coord.id, rol_id=rol_coord_a.id,
                materia_id=materia.id, carrera_id=carrera.id, cohorte_id=cohorte.id,
                desde=date(2026, 1, 1),
            )
        )
        await session.commit()

    app = FastAPI()
    app.include_router(programas_router)

    return {
        "app": app,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "materia": materia,
        "materia_b": materia_b,
        "carrera": carrera,
        "carrera_b": carrera_b,
        "cohorte": cohorte,
        "cohorte_b": cohorte_b,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_noperm": _tok(auth_noperm.id, tenant_a.id, ["ALUMNO"]),
        "tok_coord_b": _tok(auth_coord_b.id, tenant_b.id, ["COORDINADOR"]),
    }


def _payload(c: dict) -> dict:
    return {
        "materia_id": str(c["materia"].id),
        "carrera_id": str(c["carrera"].id),
        "cohorte_id": str(c["cohorte"].id),
        "titulo": "Programa 2026-1",
        "referencia_archivo": "https://storage/prog.pdf",
    }


# ---------------------------------------------------------------------------
# 6.1 RED→GREEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_programa_201_y_audit(ctx):
    """RED→GREEN: POST /api/programas → 201 con todos los campos + audit PROGRAMA_CREAR."""
    c = ctx
    sf = get_session_factory()
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/programas", json=_payload(c), headers=_auth(c["tok_coord"]))
    assert r.status_code == 201
    body = r.json()
    assert body["titulo"] == "Programa 2026-1"
    assert body["referencia_archivo"] == "https://storage/prog.pdf"
    assert uuid.UUID(body["materia_id"]) == c["materia"].id
    async with sf() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.accion == "PROGRAMA_CREAR")
        )
    assert audit is not None
    assert audit.detalle["programa_id"] == body["id"]


@pytest.mark.asyncio
async def test_crear_programa_sin_permiso_403(ctx):
    """Sin estructura:gestionar → 403."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/programas", json=_payload(c), headers=_auth(c["tok_noperm"]))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_crear_programa_campo_obligatorio_ausente_422(ctx):
    """Falta referencia_archivo → 422."""
    c = ctx
    payload = {k: v for k, v in _payload(c).items() if k != "referencia_archivo"}
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/programas", json=payload, headers=_auth(c["tok_coord"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_programa_campo_extra_422(ctx):
    """Campo extra en body → 422 (extra='forbid')."""
    c = ctx
    payload = {**_payload(c), "campo_extra": "no debería estar"}
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/programas", json=payload, headers=_auth(c["tok_coord"]))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 6.1 TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_programas_filtro_materia_y_cohorte(ctx):
    """TRIANGULATE: listar con filtro materia_id+cohorte_id retorna solo los del filtro."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post("/api/programas", json=_payload(c), headers=_auth(c["tok_coord"]))
        await cli.post(
            "/api/programas",
            json={**_payload(c), "titulo": "Otro programa"},
            headers=_auth(c["tok_coord"]),
        )
        r = await cli.get(
            "/api/programas",
            params={"materia_id": str(c["materia"].id), "cohorte_id": str(c["cohorte"].id)},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all(uuid.UUID(p["materia_id"]) == c["materia"].id for p in data)


@pytest.mark.asyncio
async def test_aislamiento_tenant_programas(ctx):
    """Tenant B no ve programas de Tenant A."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post("/api/programas", json=_payload(c), headers=_auth(c["tok_coord"]))
        payload_b = {
            "materia_id": str(c["materia_b"].id),
            "carrera_id": str(c["carrera_b"].id),
            "cohorte_id": str(c["cohorte_b"].id),
            "titulo": "Programa B",
            "referencia_archivo": "https://storage/prog-b.pdf",
        }
        await cli.post("/api/programas", json=payload_b, headers=_auth(c["tok_coord_b"]))
        r_b = await cli.get("/api/programas", headers=_auth(c["tok_coord_b"]))
    assert r_b.status_code == 200
    data_b = r_b.json()
    tenant_a_id = str(c["tenant_a"].id)
    assert all(p["tenant_id"] != tenant_a_id for p in data_b)
