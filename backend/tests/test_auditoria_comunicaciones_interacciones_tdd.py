"""C-19 Task 6.3 — estado-comunicaciones e interacciones-docente: filtros y scope."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, AuthUser, Permiso, Rol, RolPermiso, Tenant
from tests.usuarios_test_utils import clean_database, ensure_schema

_NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ctx(valid_env):
    """
    Tenant A: admin + coordinador con auditoria:ver.
    Logs sembrados:
      admin_auth:
        - 3x COMUNICACION_ENVIADA
        - 2x COMUNICACION_APROBADA
        - 4x PROGRAMA_CREAR          (no es COMUNICACION_*)
      coord_auth:
        - 1x COMUNICACION_ENVIADA
        - 5x FECHA_ACADEMICA_CREAR   (no es COMUNICACION_*)
    """
    from app.api.v1.routers.auditoria import router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as s:
        await clean_database(s)

        tenant_a = Tenant(name="Audit Comms A", slug="audit-comms-a")
        s.add(tenant_a)
        await s.flush()

        admin_auth = AuthUser(
            tenant_id=tenant_a.id, email="admin@comms-a.local",
            password_hash=hash_password("P1!"), roles=["ADMIN"],
        )
        coord_auth = AuthUser(
            tenant_id=tenant_a.id, email="coord@comms-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        s.add_all([admin_auth, coord_auth])
        await s.flush()

        rol_admin = Rol(tenant_id=tenant_a.id, nombre="ADMIN")
        rol_coord = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        s.add_all([rol_admin, rol_coord])
        await s.flush()

        perm = Permiso(tenant_id=tenant_a.id, nombre="auditoria:ver")
        s.add(perm)
        await s.flush()
        s.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_admin.id, permiso_id=perm.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=perm.id),
        ])

        # admin: comms + non-comms
        for _ in range(3):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=admin_auth.id,
                           accion="COMUNICACION_ENVIADA", fecha_hora=_NOW))
        for _ in range(2):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=admin_auth.id,
                           accion="COMUNICACION_APROBADA", fecha_hora=_NOW))
        for _ in range(4):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=admin_auth.id,
                           accion="PROGRAMA_CREAR", fecha_hora=_NOW))
        # coord: 1 comm + 5 non-comm
        s.add(AuditLog(tenant_id=tenant_a.id, actor_id=coord_auth.id,
                       accion="COMUNICACION_ENVIADA", fecha_hora=_NOW))
        for _ in range(5):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=coord_auth.id,
                           accion="FECHA_ACADEMICA_CREAR", fecha_hora=_NOW))

        admin_id = admin_auth.id
        coord_id = coord_auth.id
        await s.commit()

    app = FastAPI()
    app.include_router(router)

    return {
        "app": app,
        "tok_admin": _tok(admin_id, tenant_a.id, ["ADMIN"]),
        "tok_coord": _tok(coord_id, tenant_a.id, ["COORDINADOR"]),
        "admin_id": admin_id,
        "coord_id": coord_id,
    }


# ---------------------------------------------------------------------------
# RED → GREEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_comunicaciones_solo_comunicacion_prefijo(ctx):
    """RED→GREEN: /estado-comunicaciones retorna solo acciones COMUNICACION_*."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/estado-comunicaciones", headers=_auth(c["tok_admin"]))
    assert r.status_code == 200
    data = r.json()
    # Esperamos 3 grupos: COMUNICACION_ENVIADA (admin×3), COMUNICACION_APROBADA (admin×2),
    # COMUNICACION_ENVIADA (coord×1)
    assert all(row["accion"].startswith("COMUNICACION_") for row in data)
    # PROGRAMA_CREAR NO debe aparecer
    assert not any(row["accion"] == "PROGRAMA_CREAR" for row in data)
    # Total de grupos = 3 (admin/ENVIADA, admin/APROBADA, coord/ENVIADA)
    assert len(data) == 3


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_interacciones_docente_agrupa_correctamente(ctx):
    """TRIANGULATE: /interacciones-docente agrupa por actor+accion orden desc por total."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/interacciones-docente", headers=_auth(c["tok_admin"]))
    assert r.status_code == 200
    data = r.json()
    # Total grupos: coord/FECHA_ACADEMICA_CREAR(5), admin/PROGRAMA_CREAR(4),
    #               admin/COMUNICACION_ENVIADA(3), admin/COMUNICACION_APROBADA(2),
    #               coord/COMUNICACION_ENVIADA(1)
    assert len(data) == 5
    # Primero debe ser el de mayor total (coord FECHA_ACADEMICA_CREAR = 5)
    assert data[0]["total"] == 5
    # Segundo (admin PROGRAMA_CREAR = 4)
    assert data[1]["total"] == 4
    # Totales deben estar en orden descendente
    totales = [row["total"] for row in data]
    assert totales == sorted(totales, reverse=True)


@pytest.mark.asyncio
async def test_estado_comunicaciones_coordinador_scope(ctx):
    """TRIANGULATE: COORDINADOR en /estado-comunicaciones solo ve su COMUNICACION_ENVIADA."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/estado-comunicaciones", headers=_auth(c["tok_coord"]))
    assert r.status_code == 200
    data = r.json()
    # coord solo tiene COMUNICACION_ENVIADA×1
    assert len(data) == 1
    assert data[0]["accion"] == "COMUNICACION_ENVIADA"
    assert data[0]["total"] == 1
    assert data[0]["actor_id"] == str(c["coord_id"])


@pytest.mark.asyncio
async def test_interacciones_docente_coordinador_scope(ctx):
    """TRIANGULATE: COORDINADOR en /interacciones-docente solo ve sus propias acciones."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/interacciones-docente", headers=_auth(c["tok_coord"]))
    assert r.status_code == 200
    data = r.json()
    # coord: FECHA_ACADEMICA_CREAR(5), COMUNICACION_ENVIADA(1)
    assert len(data) == 2
    assert all(row["actor_id"] == str(c["coord_id"]) for row in data)
    totales = [row["total"] for row in data]
    assert totales == sorted(totales, reverse=True)
