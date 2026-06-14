"""C-19 Task 6.2 — /log: paginación, filtro por accion, scope COORDINADOR."""
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
      - 8 logs accion=LOG_ITEM actor=admin_auth
      - 4 logs accion=OTRO_ITEM actor=admin_auth
      - 3 logs accion=LOG_ITEM actor=coord_auth
    """
    from app.api.v1.routers.auditoria import router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as s:
        await clean_database(s)

        tenant_a = Tenant(name="Audit Log A", slug="audit-log-a")
        s.add(tenant_a)
        await s.flush()

        admin_auth = AuthUser(
            tenant_id=tenant_a.id, email="admin@log-a.local",
            password_hash=hash_password("P1!"), roles=["ADMIN"],
        )
        coord_auth = AuthUser(
            tenant_id=tenant_a.id, email="coord@log-a.local",
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

        for _ in range(8):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=admin_auth.id,
                           accion="LOG_ITEM", fecha_hora=_NOW))
        for _ in range(4):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=admin_auth.id,
                           accion="OTRO_ITEM", fecha_hora=_NOW))
        for _ in range(3):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=coord_auth.id,
                           accion="LOG_ITEM", fecha_hora=_NOW))

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
        "tenant_a": tenant_a,
    }


# ---------------------------------------------------------------------------
# RED → GREEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_default_retorna_todos_registros(ctx):
    """RED→GREEN: /log sin params retorna todos (15 < 200 default)."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/log", headers=_auth(c["tok_admin"]))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 15  # 8 + 4 + 3


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_limit_50_retorna_15(ctx):
    """TRIANGULATE: limit=50 con 15 registros retorna 15 (min(50, 15))."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/log", params={"limit": 50}, headers=_auth(c["tok_admin"]))
    assert r.status_code == 200
    assert len(r.json()) == 15


@pytest.mark.asyncio
async def test_log_limit_501_422(ctx):
    """TRIANGULATE: limit=501 supera Query(le=500) → 422."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/log", params={"limit": 501}, headers=_auth(c["tok_admin"]))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_log_filtro_por_accion(ctx):
    """TRIANGULATE: filtro accion=LOG_ITEM retorna solo esos (11 de 15)."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            "/api/auditoria/log",
            params={"accion": "LOG_ITEM"},
            headers=_auth(c["tok_admin"]),
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 11  # 8 admin + 3 coord
    assert all(row["accion"] == "LOG_ITEM" for row in data)


@pytest.mark.asyncio
async def test_log_coordinador_scope_propio(ctx):
    """TRIANGULATE: COORDINADOR en /log ve solo sus propios registros."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/log", headers=_auth(c["tok_coord"]))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3  # solo los 3 de coord_auth
    assert all(row["actor_id"] == str(c["coord_id"]) for row in data)
