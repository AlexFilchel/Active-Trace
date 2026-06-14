"""Tests C-16 tareas-internas — tasks 6.3 (mis-tareas), 6.4 (admin), 6.5 (comentarios)."""
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
    """Two tenants. Tenant A: coord, prof1, prof2. Tenant B: coord_b."""
    from app.api.v1.routers.tareas import router as tareas_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant ListTareasA", slug="list-tareas-a")
        tenant_b = Tenant(name="Tenant ListTareasB", slug="list-tareas-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@list-tareas-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_prof1 = AuthUser(
            tenant_id=tenant_a.id, email="prof1@list-tareas-a.local",
            password_hash=hash_password("P1!"), roles=["PROFESOR"],
        )
        auth_prof2 = AuthUser(
            tenant_id=tenant_a.id, email="prof2@list-tareas-a.local",
            password_hash=hash_password("P1!"), roles=["PROFESOR"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@list-tareas-b.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        session.add_all([auth_coord, auth_prof1, auth_prof2, auth_coord_b])
        await session.flush()

        rol_coord_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_prof_a = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        rol_coord_b = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
        session.add_all([rol_coord_a, rol_prof_a, rol_coord_b])
        await session.flush()

        perm_a = Permiso(tenant_id=tenant_a.id, nombre="tareas:gestionar")
        perm_b = Permiso(tenant_id=tenant_b.id, nombre="tareas:gestionar")
        session.add_all([perm_a, perm_b])
        await session.flush()
        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord_a.id, permiso_id=perm_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_prof_a.id, permiso_id=perm_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_coord_b.id, permiso_id=perm_b.id),
        ])

        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CRR-LA", nombre="Carrera A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRR-LB", nombre="Carrera B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera_a.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-LA", nombre="Materia A")
        cohorte_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=carrera_b.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-LB", nombre="Materia B")
        session.add_all([cohorte_a, materia_a, cohorte_b, materia_b])
        await session.flush()

        u_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="A",
            email_encrypted="enc-coord-la", email_hash="hash-coord-la",
        )
        u_prof1 = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_prof1.id,
            nombre="Prof", apellidos="Uno",
            email_encrypted="enc-p1-la", email_hash="hash-p1-la",
        )
        u_prof2 = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_prof2.id,
            nombre="Prof", apellidos="Dos",
            email_encrypted="enc-p2-la", email_hash="hash-p2-la",
        )
        u_coord_b = Usuario(
            tenant_id=tenant_b.id, auth_user_id=auth_coord_b.id,
            nombre="CoordB", apellidos="B",
            email_encrypted="enc-coord-lb", email_hash="hash-coord-lb",
        )
        session.add_all([u_coord, u_prof1, u_prof2, u_coord_b])
        await session.flush()
        session.add_all([
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_coord.id, rol_id=rol_coord_a.id,
                materia_id=materia_a.id, carrera_id=carrera_a.id, cohorte_id=cohorte_a.id,
                desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_prof1.id, rol_id=rol_prof_a.id,
                materia_id=materia_a.id, carrera_id=carrera_a.id, cohorte_id=cohorte_a.id,
                desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_prof2.id, rol_id=rol_prof_a.id,
                materia_id=materia_a.id, carrera_id=carrera_a.id, cohorte_id=cohorte_a.id,
                desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant_b.id, usuario_id=u_coord_b.id, rol_id=rol_coord_b.id,
                materia_id=materia_b.id, carrera_id=carrera_b.id, cohorte_id=cohorte_b.id,
                desde=date(2026, 1, 1),
            ),
        ])
        await session.commit()

    app = FastAPI()
    app.include_router(tareas_router)

    return {
        "app": app,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "materia_a": materia_a,
        "u_coord": u_coord,
        "u_prof1": u_prof1,
        "u_prof2": u_prof2,
        "u_coord_b": u_coord_b,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_prof1": _tok(auth_prof1.id, tenant_a.id, ["PROFESOR"]),
        "tok_prof2": _tok(auth_prof2.id, tenant_a.id, ["PROFESOR"]),
        "tok_coord_b": _tok(auth_coord_b.id, tenant_b.id, ["COORDINADOR"]),
    }


# ---------------------------------------------------------------------------
# 6.3 — Mis tareas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mis_tareas_solo_las_propias(ctx):
    """RED→GREEN: usuario ve solo tareas donde es asignado_a o asignado_por."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        # coord asigna tarea a prof1
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Para prof1"},
            headers=_auth(c["tok_coord"]),
        )
        # prof1 asigna tarea a prof2 (prof1 es asignado_por)
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof2"].id), "descripcion": "Prof1 asigna a Prof2"},
            headers=_auth(c["tok_prof1"]),
        )
        # prof2 no debería ver la tarea de coord→prof1
        r_prof1 = await cli.get("/api/tareas/mis-tareas", headers=_auth(c["tok_prof1"]))
        r_prof2 = await cli.get("/api/tareas/mis-tareas", headers=_auth(c["tok_prof2"]))
    # prof1 es asignado_a de la primera Y asignado_por de la segunda → ve 2
    assert r_prof1.status_code == 200
    assert len(r_prof1.json()) == 2
    # prof2 es asignado_a de la segunda → ve 1
    assert r_prof2.status_code == 200
    assert len(r_prof2.json()) == 1


@pytest.mark.asyncio
async def test_mis_tareas_filtro_estado(ctx):
    """TRIANGULATE: filtro por estado=Pendiente."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea filtro"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        await cli.patch(
            f"/api/tareas/{tarea_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
        r_pendiente = await cli.get(
            "/api/tareas/mis-tareas?estado=Pendiente",
            headers=_auth(c["tok_prof1"]),
        )
        r_en_progreso = await cli.get(
            "/api/tareas/mis-tareas?estado=En progreso",
            headers=_auth(c["tok_prof1"]),
        )
    pendiente_ids = [t["id"] for t in r_pendiente.json()]
    assert tarea_id not in pendiente_ids
    en_progreso_ids = [t["id"] for t in r_en_progreso.json()]
    assert tarea_id in en_progreso_ids


@pytest.mark.asyncio
async def test_mis_tareas_filtro_materia(ctx):
    """Filtro por materia_id devuelve solo tareas de esa materia."""
    c = ctx
    materia_id = str(c["materia_a"].id)
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Con materia", "materia_id": materia_id},
            headers=_auth(c["tok_coord"]),
        )
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Sin materia"},
            headers=_auth(c["tok_coord"]),
        )
        r = await cli.get(
            f"/api/tareas/mis-tareas?materia_id={materia_id}",
            headers=_auth(c["tok_prof1"]),
        )
    assert r.status_code == 200
    assert all(t["materia_id"] == materia_id for t in r.json())
    assert len(r.json()) == 1


# ---------------------------------------------------------------------------
# 6.4 — Administración
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_ve_todas_las_tareas_del_tenant(ctx):
    """COORDINADOR ve todas las tareas del tenant."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "T1"},
            headers=_auth(c["tok_coord"]),
        )
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof2"].id), "descripcion": "T2"},
            headers=_auth(c["tok_prof1"]),
        )
        r = await cli.get("/api/tareas", headers=_auth(c["tok_coord"]))
    assert r.status_code == 200
    assert len(r.json()) >= 2


@pytest.mark.asyncio
async def test_admin_filtros_combinados(ctx):
    """TRIANGULATE: filtros asignado_a + estado en AND."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "P1 pend"},
            headers=_auth(c["tok_coord"]),
        )
        r_crear2 = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "P1 prog"},
            headers=_auth(c["tok_coord"]),
        )
        t2_id = r_crear2.json()["id"]
        await cli.patch(
            f"/api/tareas/{t2_id}/estado",
            json={"estado": "En progreso"},
            headers=_auth(c["tok_prof1"]),
        )
        r = await cli.get(
            f"/api/tareas?asignado_a={c['u_prof1'].id}&estado=Pendiente",
            headers=_auth(c["tok_coord"]),
        )
    bodies = r.json()
    assert all(b["asignado_a"] == str(c["u_prof1"].id) for b in bodies)
    assert all(b["estado"] == "Pendiente" for b in bodies)


@pytest.mark.asyncio
async def test_admin_aislamiento_de_tenant(ctx):
    """Tarea de tenant_b no aparece en listado de tenant_a."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_coord_b"].id), "descripcion": "Tarea B"},
            headers=_auth(c["tok_coord_b"]),
        )
        r = await cli.get("/api/tareas", headers=_auth(c["tok_coord"]))
    tenant_a_id = str(c["tenant_a"].id)
    assert all(t["tenant_id"] == tenant_a_id for t in r.json())


# ---------------------------------------------------------------------------
# 6.5 — Comentarios
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agregar_comentario_201_con_audit(ctx):
    """RED→GREEN: agregar comentario → 201, audit TAREA_COMENTAR."""
    c = ctx
    sf = get_session_factory()
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea comentarios"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        r = await cli.post(
            f"/api/tareas/{tarea_id}/comentarios",
            json={"texto": "Primer comentario"},
            headers=_auth(c["tok_prof1"]),
        )
    assert r.status_code == 201
    assert r.json()["texto"] == "Primer comentario"
    async with sf() as session:
        from sqlalchemy import select
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.accion == "TAREA_COMENTAR")
        )
    assert audit is not None
    assert audit.detalle["tarea_id"] == tarea_id


@pytest.mark.asyncio
async def test_listar_comentarios_orden_cronologico(ctx):
    """TRIANGULATE: listar comentarios en orden cronológico ascendente."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea orden"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        await cli.post(
            f"/api/tareas/{tarea_id}/comentarios",
            json={"texto": "Comentario 1"},
            headers=_auth(c["tok_coord"]),
        )
        await cli.post(
            f"/api/tareas/{tarea_id}/comentarios",
            json={"texto": "Comentario 2"},
            headers=_auth(c["tok_prof1"]),
        )
        r = await cli.get(
            f"/api/tareas/{tarea_id}/comentarios",
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 200
    textos = [c_item["texto"] for c_item in r.json()]
    assert textos[0] == "Comentario 1"
    assert textos[1] == "Comentario 2"


@pytest.mark.asyncio
async def test_comentario_texto_vacio_422(ctx):
    """Texto vacío → 422."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_prof1"].id), "descripcion": "Tarea vacio"},
            headers=_auth(c["tok_coord"]),
        )
        tarea_id = r_crear.json()["id"]
        r = await cli.post(
            f"/api/tareas/{tarea_id}/comentarios",
            json={"texto": ""},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_comentario_en_tarea_de_otro_tenant_404(ctx):
    """Comentar en tarea de otro tenant → 404."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear_b = await cli.post(
            "/api/tareas",
            json={"asignado_a": str(c["u_coord_b"].id), "descripcion": "Tarea tenant B"},
            headers=_auth(c["tok_coord_b"]),
        )
        tarea_b_id = r_crear_b.json()["id"]
        r = await cli.post(
            f"/api/tareas/{tarea_b_id}/comentarios",
            json={"texto": "Intruso"},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 404
