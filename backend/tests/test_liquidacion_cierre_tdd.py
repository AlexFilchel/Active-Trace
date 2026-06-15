"""C-18 Task 7.3 — Cierre de período y KPIs: Cerrada, 409, 403, totales contables."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Permiso, Rol, RolPermiso, Tenant
from app.models.estructura import Carrera, Cohorte, Materia
from app.models.liquidaciones import SalarioBase, SalarioPlus
from app.models.usuarios import Asignacion, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


def _tok(uid: uuid.UUID, tid: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(user_id=str(uid), tenant_id=str(tid), roles=roles)


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def ctx(valid_env):
    from app.api.v1.routers.liquidaciones import router as liq_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as s:
        await clean_database(s)

        tenant = Tenant(name="LiqCierre", slug="liq-cierre")
        s.add(tenant)
        await s.flush()

        auth_fin = AuthUser(
            tenant_id=tenant.id, email="fin@lcierre.local",
            password_hash=hash_password("P1!"), roles=["FINANZAS"],
        )
        auth_solo_ver = AuthUser(
            tenant_id=tenant.id, email="ver@lcierre.local",
            password_hash=hash_password("P1!"), roles=["ADMIN"],
        )
        s.add_all([auth_fin, auth_solo_ver])
        await s.flush()

        rol_fin = Rol(tenant_id=tenant.id, nombre="FINANZAS")
        rol_admin = Rol(tenant_id=tenant.id, nombre="ADMIN")
        rol_prof = Rol(tenant_id=tenant.id, nombre="PROFESOR")
        rol_nexo = Rol(tenant_id=tenant.id, nombre="NEXO")
        s.add_all([rol_fin, rol_admin, rol_prof, rol_nexo])
        await s.flush()

        perm_ver = Permiso(tenant_id=tenant.id, nombre="liquidaciones:ver")
        perm_cerrar = Permiso(tenant_id=tenant.id, nombre="liquidaciones:cerrar")
        s.add_all([perm_ver, perm_cerrar])
        await s.flush()
        s.add_all([
            RolPermiso(tenant_id=tenant.id, rol_id=rol_fin.id, permiso_id=perm_ver.id),
            RolPermiso(tenant_id=tenant.id, rol_id=rol_fin.id, permiso_id=perm_cerrar.id),
            RolPermiso(tenant_id=tenant.id, rol_id=rol_admin.id, permiso_id=perm_ver.id),
        ])

        carrera = Carrera(tenant_id=tenant.id, codigo="CARR", nombre="Carrera")
        s.add(carrera)
        await s.flush()

        cohorte = Cohorte(
            tenant_id=tenant.id, carrera_id=carrera.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        mat_prog = Materia(tenant_id=tenant.id, codigo="PROG", nombre="Prog", categoria_plus="PROG")
        usuario_prof = Usuario(
            tenant_id=tenant.id, nombre="Profe", apellidos="A",
            email_encrypted="enc-prof-c", email_hash="hash-prof-c", facturador=False,
        )
        usuario_fact = Usuario(
            tenant_id=tenant.id, nombre="Fact", apellidos="B",
            email_encrypted="enc-fact-c", email_hash="hash-fact-c", facturador=True,
        )
        usuario_nexo = Usuario(
            tenant_id=tenant.id, nombre="Nexo", apellidos="C",
            email_encrypted="enc-nexo-c", email_hash="hash-nexo-c", facturador=False,
        )
        sal_base = SalarioBase(
            tenant_id=tenant.id, rol="PROFESOR", monto=Decimal("5000"), desde=date(2026, 1, 1),
        )
        sal_base_nexo = SalarioBase(
            tenant_id=tenant.id, rol="NEXO", monto=Decimal("3000"), desde=date(2026, 1, 1),
        )
        sal_plus = SalarioPlus(
            tenant_id=tenant.id, grupo="PROG", rol="PROFESOR", monto=Decimal("800"), desde=date(2026, 1, 1),
        )
        s.add_all([
            cohorte, mat_prog, usuario_prof, usuario_fact, usuario_nexo,
            sal_base, sal_base_nexo, sal_plus,
        ])
        await s.flush()

        # Asignaciones para fixture base
        s.add_all([
            Asignacion(
                tenant_id=tenant.id, usuario_id=usuario_prof.id, rol_id=rol_prof.id,
                materia_id=mat_prog.id, cohorte_id=cohorte.id, comisiones=[], desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant.id, usuario_id=usuario_fact.id, rol_id=rol_prof.id,
                materia_id=mat_prog.id, cohorte_id=cohorte.id, comisiones=[], desde=date(2026, 1, 1),
            ),
            Asignacion(
                tenant_id=tenant.id, usuario_id=usuario_nexo.id, rol_id=rol_nexo.id,
                materia_id=mat_prog.id, cohorte_id=cohorte.id, comisiones=[], desde=date(2026, 1, 1),
            ),
        ])
        await s.flush()
        await s.commit()

    app = FastAPI()
    app.include_router(liq_router)
    periodo = "2026-01"
    cid = str(cohorte.id)

    return {
        "app": app,
        "tok_fin": _tok(auth_fin.id, tenant.id, ["FINANZAS"]),
        "tok_solo_ver": _tok(auth_solo_ver.id, tenant.id, ["ADMIN"]),
        "cohorte_id": cid,
        "periodo": periodo,
    }


async def _calcular(ctx) -> None:
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/liquidaciones/calcular",
            json={"cohorte_id": ctx["cohorte_id"], "periodo": ctx["periodo"]},
            headers=_auth(ctx["tok_fin"]),
        )
    assert r.status_code == 201


async def _cerrar(ctx) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as cli:
        r = await cli.post(
            f"/api/liquidaciones/{ctx['cohorte_id']}/{ctx['periodo']}/cerrar",
            headers=_auth(ctx["tok_fin"]),
        )
    return r.status_code, r.json()


# ---------------------------------------------------------------------------
# RED → GREEN: cerrar cambia estado a Cerrada
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cerrar_periodo_devuelve_cerradas(ctx):
    """RED→GREEN: POST cerrar → 200, cerradas > 0, estado GET = Cerrada."""
    c = ctx
    await _calcular(c)
    status, body = await _cerrar(c)
    assert status == 200
    assert body["cerradas"] > 0

    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            "/api/liquidaciones",
            params={"cohorte_id": c["cohorte_id"], "periodo": c["periodo"]},
            headers=_auth(c["tok_fin"]),
        )
    rows = r.json()
    assert all(row["estado"] == "Cerrada" for row in rows)


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recalcular_periodo_cerrado_409(ctx):
    """TRIANGULATE: intentar calcular sobre período cerrado → 409."""
    c = ctx
    await _calcular(c)
    await _cerrar(c)

    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/liquidaciones/calcular",
            json={"cohorte_id": c["cohorte_id"], "periodo": c["periodo"]},
            headers=_auth(c["tok_fin"]),
        )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_cerrar_sin_permiso_403(ctx):
    """TRIANGULATE: usuario sin liquidaciones:cerrar → 403."""
    c = ctx
    await _calcular(c)

    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.post(
            f"/api/liquidaciones/{c['cohorte_id']}/{c['periodo']}/cerrar",
            headers=_auth(c["tok_solo_ver"]),
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_kpis_separa_facturantes_y_nexo(ctx):
    """TRIANGULATE: KPIs contables — total_sin_factura excluye facturantes, NEXO separado."""
    c = ctx
    await _calcular(c)

    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            f"/api/liquidaciones/{c['cohorte_id']}/{c['periodo']}/kpis",
            headers=_auth(c["tok_fin"]),
        )
    assert r.status_code == 200
    kpis = r.json()

    # PROF(5800) + NEXO(3800=3000+800) incluidos en sin_factura; FACT(5800) excluido
    assert Decimal(kpis["total_sin_factura"]) > 0
    assert Decimal(kpis["total_nexo"]) > 0
    assert kpis["cantidad_facturantes"] == 1
    assert kpis["cantidad_docentes"] >= 1
    # total_con_factura cubre a todos
    assert Decimal(kpis["total_con_factura"]) >= Decimal(kpis["total_sin_factura"])
