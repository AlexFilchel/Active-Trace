"""Tests C-17 — task 6.2: FechaAcademica CRUD."""
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
from app.models.programas import FechaAcademica
from app.models.usuarios import Asignacion
from tests.usuarios_test_utils import clean_database, ensure_schema


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ctx(valid_env):
    """Tenant A: coordinador. Tenant B: coordinador_b."""
    from app.api.v1.routers.programas import fechas_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant FechasA", slug="fechas-a")
        tenant_b = Tenant(name="Tenant FechasB", slug="fechas-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@fechas-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@fechas-b.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        session.add_all([auth_coord, auth_coord_b])
        await session.flush()

        rol_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_b = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
        session.add_all([rol_a, rol_b])
        await session.flush()

        perm_a = Permiso(tenant_id=tenant_a.id, nombre="estructura:gestionar")
        perm_b = Permiso(tenant_id=tenant_b.id, nombre="estructura:gestionar")
        session.add_all([perm_a, perm_b])
        await session.flush()
        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_a.id, permiso_id=perm_a.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_b.id, permiso_id=perm_b.id),
        ])

        carrera = Carrera(tenant_id=tenant_a.id, codigo="CRR-F", nombre="Carrera Fechas")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRR-FB", nombre="Carrera Fechas B")
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
        materia = Materia(tenant_id=tenant_a.id, codigo="MAT-F", nombre="Materia Fechas")
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-FB", nombre="Materia Fechas B")
        session.add_all([cohorte, cohorte_b, materia, materia_b])
        await session.flush()

        u_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="F",
            email_encrypted="enc-cf", email_hash="hash-cf",
        )
        session.add(u_coord)
        await session.flush()
        session.add(
            Asignacion(
                tenant_id=tenant_a.id, usuario_id=u_coord.id, rol_id=rol_a.id,
                materia_id=materia.id, carrera_id=carrera.id, cohorte_id=cohorte.id,
                desde=date(2026, 1, 1),
            )
        )

        # Pre-create a FechaAcademica in tenant B for aislamiento tests
        fecha_b = FechaAcademica(
            tenant_id=tenant_b.id,
            materia_id=materia_b.id,
            cohorte_id=cohorte_b.id,
            tipo="Parcial",
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="Parcial B",
        )
        session.add(fecha_b)
        await session.commit()

        fecha_b_id = fecha_b.id

    app = FastAPI()
    app.include_router(fechas_router)

    return {
        "app": app,
        "materia": materia,
        "cohorte": cohorte,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_coord_b": _tok(auth_coord_b.id, tenant_b.id, ["COORDINADOR"]),
        "fecha_b_id": fecha_b_id,
    }


def _payload(c: dict) -> dict:
    return {
        "materia_id": str(c["materia"].id),
        "cohorte_id": str(c["cohorte"].id),
        "tipo": "Parcial",
        "numero": 1,
        "periodo": "2026-1",
        "fecha": "2026-04-15",
        "titulo": "Primer Parcial",
    }


# ---------------------------------------------------------------------------
# 6.2 RED→GREEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_fecha_201_y_audit(ctx):
    """RED→GREEN: POST /api/fechas-academicas → 201 + audit FECHA_ACAT_CREAR."""
    c = ctx
    sf = get_session_factory()
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/fechas-academicas", json=_payload(c), headers=_auth(c["tok_coord"]))
    assert r.status_code == 201
    body = r.json()
    assert body["tipo"] == "Parcial"
    assert body["numero"] == 1
    assert body["periodo"] == "2026-1"
    assert body["titulo"] == "Primer Parcial"
    async with sf() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.accion == "FECHA_ACAT_CREAR")
        )
    assert audit is not None
    assert audit.detalle["fecha_id"] == body["id"]


@pytest.mark.asyncio
async def test_tipo_invalido_422(ctx):
    """tipo no en Literal[Parcial/TP/Coloquio/Recuperatorio] → 422."""
    c = ctx
    payload = {**_payload(c), "tipo": "Examen"}
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/fechas-academicas", json=payload, headers=_auth(c["tok_coord"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_numero_cero_422(ctx):
    """numero=0 (< ge=1) → 422."""
    c = ctx
    payload = {**_payload(c), "numero": 0}
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post("/api/fechas-academicas", json=payload, headers=_auth(c["tok_coord"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_editar_fecha_200_y_audit(ctx):
    """PATCH /api/fechas-academicas/{id} → 200 + audit FECHA_ACAT_EDITAR."""
    c = ctx
    sf = get_session_factory()
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r_crear = await cli.post(
            "/api/fechas-academicas", json=_payload(c), headers=_auth(c["tok_coord"])
        )
        fecha_id = r_crear.json()["id"]
        r_edit = await cli.patch(
            f"/api/fechas-academicas/{fecha_id}",
            json={"titulo": "Parcial Actualizado", "fecha": "2026-04-20"},
            headers=_auth(c["tok_coord"]),
        )
    assert r_edit.status_code == 200
    body = r_edit.json()
    assert body["titulo"] == "Parcial Actualizado"
    assert body["fecha"] == "2026-04-20"
    async with sf() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.accion == "FECHA_ACAT_EDITAR")
        )
    assert audit is not None
    assert audit.detalle["fecha_id"] == fecha_id


@pytest.mark.asyncio
async def test_editar_fecha_otro_tenant_404(ctx):
    """PATCH de fecha perteneciente a otro tenant → 404 (row-level isolation)."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.patch(
            f"/api/fechas-academicas/{c['fecha_b_id']}",
            json={"titulo": "Hack"},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 6.2 TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_filtrado_tipo_y_periodo(ctx):
    """TRIANGULATE: GET con tipo+periodo retorna solo los que coinciden."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post("/api/fechas-academicas", json=_payload(c), headers=_auth(c["tok_coord"]))
        await cli.post(
            "/api/fechas-academicas",
            json={**_payload(c), "tipo": "TP", "numero": 1, "titulo": "TP 1"},
            headers=_auth(c["tok_coord"]),
        )
        await cli.post(
            "/api/fechas-academicas",
            json={**_payload(c), "periodo": "2026-2", "titulo": "Parcial 2026-2"},
            headers=_auth(c["tok_coord"]),
        )
        r = await cli.get(
            "/api/fechas-academicas",
            params={"tipo": "Parcial", "periodo": "2026-1"},
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["tipo"] == "Parcial"
    assert data[0]["periodo"] == "2026-1"
