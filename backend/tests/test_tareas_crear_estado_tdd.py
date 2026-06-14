"""Tests C-16 tareas-internas — tasks 6.1 (crear) y 6.2 (máquina de estados)."""
from __future__ import annotations

import uuid
from datetime import date

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


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ctx(valid_env):
    """Tenant A: coordinador, profesor1, profesor2. Tenant B: coordinador_b."""
    from app.api.v1.routers.tareas import router as tareas_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant TareasA", slug="tareas-a")
        tenant_b = Tenant(name="Tenant TareasB", slug="tareas-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@tareas-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_prof1 = AuthUser(
            tenant_id=tenant_a.id, email="prof1@tareas-a.local",
            password_hash=hash_password("P1!"), roles=["PROFESOR"],
        )
        auth_prof2 = AuthUser(
            tenant_id=tenant_a.id, email="prof2@tareas-a.local",
            password_hash=hash_password("P1!"), roles=["PROFESOR"],
        )
        auth_noperm = AuthUser(
            tenant_id=tenant_a.id, email="noperm@tareas-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        session.add_all([auth_coord, auth_prof1, auth_prof2, auth_noperm])
        await session.flush()

        rol_coord = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_prof = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        session.add_all([rol_coord, rol_prof])
        await session.flush()

        perm = Permiso(tenant_id=tenant_a.id, nombre="tareas:gestionar")
        session.add(perm)
        await session.flush()
        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=perm.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_prof.id, permiso_id=perm.id),
        ])

        carrera = Carrera(tenant_id=tenant_a.id, codigo="CRR-T", nombre="Carrera Tareas")
        session.add(carrera)
        await session.flush()

        cohorte = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia = Materia(tenant_id=tenant_a.id, codigo="MAT-T", nombre="Materia Tareas")
        session.add_all([cohorte, materia])
        await session.flush()

        u_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="T",
            email_encrypted="enc-coord-t", email_hash="hash-coord-t",
        )
        u_prof1 = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_prof1.id,
            nombre="Prof", apellidos="Uno",
            email_encrypted="enc-p1-t", email_hash="hash-p1-t",
        )
        u_prof2 = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_prof2.id,
            nombre="Prof", apellidos="Dos",
            email_encrypted="enc-p2-t", email_hash="hash-p2-t",
        )
        u_noperm = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_noperm.id,
            nombre="No", apellidos="Perm",
            email_encrypted="enc-np-t", email_hash="hash-np-t",
        )
        session.add_all([u_coord, u_prof1, u_prof2, u_noperm])
        await session.flush()
        session.add_all([
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_coord.id, rol_id=rol_coord.id,
                materia_id=materia.id, carrera_id=carrera.id, cohorte_id=cohorte.id,
                desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_prof1.id, rol_id=rol_prof.id,
                materia_id=materia.id, carrera_id=carrera.id, cohorte_id=cohorte.id,
                desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_prof2.id, rol_id=rol_prof.id,
                materia_id=materia.id, carrera_id=carrera.id, cohorte_id=cohorte.id,
                desde=date(2026, 1, 1),
            ),
        ])
        await session.commit()

    app = FastAPI()
    app.include_router(tareas_router)

    return {
        "app": app,
        "tenant_a": tenant_a,
        "materia": materia,
        "u_coord": u_coord,
        "u_prof1": u_prof1,
        "u_prof2": u_prof2,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_prof1": _tok(auth_prof1.id, tenant_a.id, ["PROFESOR"]),
        "tok_prof2": _tok(auth_prof2.id, tenant_a.id, ["PROFESOR"]),
        "tok_noperm": _tok(auth_noperm.id, tenant_a.id, ["ALUMNO"]),
    }


# ---------------------------------------------------------------------------
# 6.1 — Crear tarea
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_tarea_estado_pendiente(ctx):
    """RED→GREEN: crear tarea devuelve 201, estado=Pendiente, asignado_por=coord."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Revisar entregas"},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 201
    body = r.json()
    assert body["estado"] == "Pendiente"
    assert uuid.UUID(body["asignado_por"]) == c["u_coord"].id
    assert uuid.UUID(body["asignado_a"]) == c["u_prof1"].id


@pytest.mark.asyncio
async def test_crear_tarea_con_materia_id(ctx):
    """TRIANGULATE: tarea con materia_id se guarda correctamente."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/tareas",
            json={
                "asignado_a": str(c["u_prof1"].id),
                "descripcion": "Corregir parcial",
                "materia_id": str(c["materia"].id),
            },
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 201
    assert uuid.UUID(r.json()["materia_id"]) == c["materia"].id


@pytest.mark.asyncio
async def test_crear_tarea_sin_permiso_403(ctx):
    """Sin permiso tareas:gestionar → 403."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "X"},
            headers=_auth(c["tok_noperm"]),
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_crear_tarea_descripcion_vacia_422(ctx):
    """Descripción vacía → 422."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": ""},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_tarea_campo_extra_422(ctx):
    """Campo extra → 422 (extra='forbid')."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "X", "campo_extra": "Y"},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 6.2 — Máquina de estados
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transicion_pendiente_a_en_progreso(ctx):
    """RED→GREEN: asignado_a avanza Pendiente→En progreso → 200."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea A"},
            headers=_auth(c["tok_coord"]),
        )
        assert r_crear.status_code == 201
        tarea_id = r_crear.json()["id"]

        r = await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
    assert r.status_code == 200
    assert r.json()["estado"] == "En progreso"


@pytest.mark.asyncio
async def test_transicion_en_progreso_a_resuelta(ctx):
    """TRIANGULATE: En progreso→Resuelta válido."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea B"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
        r = await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "Resuelta"},
            headers=_auth(c["tok_prof1"]),
        )
    assert r.status_code == 200
    assert r.json()["estado"] == "Resuelta"


@pytest.mark.asyncio
async def test_transicion_invalida_resuelta_a_en_progreso_422(ctx):
    """Resuelta→En progreso → 422."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea C"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
        await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "Resuelta"},
            headers=_auth(c["tok_prof1"]),
        )
        r = await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_cancelar_por_asignador(ctx):
    """Asignador (coord) puede cancelar una tarea Pendiente."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea D"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        r = await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "Cancelada"},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 200
    assert r.json()["estado"] == "Cancelada"


@pytest.mark.asyncio
async def test_audit_tarea_estado_contiene_estados(ctx):
    """Audit TAREA_ESTADO registra estado_anterior y estado_nuevo."""
    c = ctx
    sf = get_session_factory()
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea E"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
    async with sf() as session:
        audit = await session.scalar(
            __import__("sqlalchemy", fromlist=["select"]).select(AuditLog)
            .where(AuditLog.accion == "TAREA_ESTADO")
        )
    assert audit is not None
    assert audit.detalle["estado_anterior"] == "Pendiente"
    assert audit.detalle["estado_nuevo"] == "En progreso"
    assert audit.detalle["tarea_id"] == tarea_id
