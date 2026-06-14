"""C-19 Task 6.1 — acciones-por-dia: scope COORDINADOR vs ADMIN, filtro por fecha, 403."""
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

_D1 = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
_D2 = datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc)


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def ctx(valid_env):
    """
    Tenant A: admin + coordinador + noperm, ambos con auditoria:ver (admin y coord).
    AuditLogs sembrados:
      - actor = admin_auth: 3 registros en D1
      - actor = coord_auth: 2 registros en D1, 1 en D2
    Tenant B: admin_b sin permiso relevante (para aislamiento).
    """
    from app.api.v1.routers.auditoria import router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as s:
        await clean_database(s)

        tenant_a = Tenant(name="Audit Scope A", slug="audit-scope-a")
        tenant_b = Tenant(name="Audit Scope B", slug="audit-scope-b")
        s.add_all([tenant_a, tenant_b])
        await s.flush()

        admin_auth = AuthUser(
            tenant_id=tenant_a.id, email="admin@aud-a.local",
            password_hash=hash_password("P1!"), roles=["ADMIN"],
        )
        coord_auth = AuthUser(
            tenant_id=tenant_a.id, email="coord@aud-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        noperm_auth = AuthUser(
            tenant_id=tenant_a.id, email="noperm@aud-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        s.add_all([admin_auth, coord_auth, noperm_auth])
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

        # Seed audit logs
        for _ in range(3):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=admin_auth.id,
                           accion="TEST_A", fecha_hora=_D1))
        for _ in range(2):
            s.add(AuditLog(tenant_id=tenant_a.id, actor_id=coord_auth.id,
                           accion="TEST_A", fecha_hora=_D1))
        s.add(AuditLog(tenant_id=tenant_a.id, actor_id=coord_auth.id,
                       accion="TEST_A", fecha_hora=_D2))

        await s.commit()

    app = FastAPI()
    app.include_router(router)

    return {
        "app": app,
        "tenant_a": tenant_a,
        "tok_admin": _tok(admin_auth.id, tenant_a.id, ["ADMIN"]),
        "tok_coord": _tok(coord_auth.id, tenant_a.id, ["COORDINADOR"]),
        "tok_noperm": _tok(noperm_auth.id, tenant_a.id, ["ALUMNO"]),
    }


# ---------------------------------------------------------------------------
# RED → GREEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_ve_todos_actores_agrupados(ctx):
    """RED→GREEN: ADMIN recibe acciones de TODOS los actores del tenant."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/acciones-por-dia", headers=_auth(c["tok_admin"]))
    assert r.status_code == 200
    data = r.json()
    # D1: 3 (admin) + 2 (coord) = 5, D2: 1 (coord)
    totales = {row["fecha"]: row["total"] for row in data}
    assert totales["2026-06-10"] == 5
    assert totales["2026-06-14"] == 1


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coordinador_scope_propio(ctx):
    """TRIANGULATE: COORDINADOR solo ve sus propias acciones (D2)."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/acciones-por-dia", headers=_auth(c["tok_coord"]))
    assert r.status_code == 200
    data = r.json()
    # coord: 2 en D1, 1 en D2
    totales = {row["fecha"]: row["total"] for row in data}
    assert totales.get("2026-06-10") == 2
    assert totales.get("2026-06-14") == 1
    # No debe incluir los 3 del admin
    assert totales.get("2026-06-10", 0) < 5


@pytest.mark.asyncio
async def test_admin_filtro_fecha_desde(ctx):
    """TRIANGULATE: filtro desde=2026-06-14 solo retorna D2."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            "/api/auditoria/acciones-por-dia",
            params={"desde": "2026-06-14"},
            headers=_auth(c["tok_admin"]),
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["fecha"] == "2026-06-14"
    assert data[0]["total"] == 1


@pytest.mark.asyncio
async def test_sin_permiso_403(ctx):
    """TRIANGULATE: usuario sin auditoria:ver recibe 403."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get("/api/auditoria/acciones-por-dia", headers=_auth(c["tok_noperm"]))
    assert r.status_code == 403
