"""C-18 Task 7.2 — Cálculo de liquidaciones: base, plus, facturador, idempotencia, 409."""
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

        tenant = Tenant(name="LiqCalc", slug="liq-calc")
        s.add(tenant)
        await s.flush()

        auth_fin = AuthUser(
            tenant_id=tenant.id, email="fin@lc.local",
            password_hash=hash_password("P1!"), roles=["FINANZAS"],
        )
        s.add(auth_fin)
        await s.flush()

        rol_fin = Rol(tenant_id=tenant.id, nombre="FINANZAS")
        rol_prof = Rol(tenant_id=tenant.id, nombre="PROFESOR")
        s.add_all([rol_fin, rol_prof])
        await s.flush()

        perm_ver = Permiso(tenant_id=tenant.id, nombre="liquidaciones:ver")
        perm_cerrar = Permiso(tenant_id=tenant.id, nombre="liquidaciones:cerrar")
        s.add_all([perm_ver, perm_cerrar])
        await s.flush()
        s.add_all([
            RolPermiso(tenant_id=tenant.id, rol_id=rol_fin.id, permiso_id=perm_ver.id),
            RolPermiso(tenant_id=tenant.id, rol_id=rol_fin.id, permiso_id=perm_cerrar.id),
        ])

        carrera = Carrera(tenant_id=tenant.id, codigo="CAR01", nombre="Carrera Test")
        s.add(carrera)
        await s.flush()

        cohorte = Cohorte(
            tenant_id=tenant.id, carrera_id=carrera.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        mat_prog = Materia(tenant_id=tenant.id, codigo="PROG", nombre="Prog", categoria_plus="PROG")
        mat_prog2 = Materia(tenant_id=tenant.id, codigo="PROG2", nombre="Prog 2", categoria_plus="PROG")
        mat_mate = Materia(tenant_id=tenant.id, codigo="MATE", nombre="Mate", categoria_plus=None)
        usuario_prof = Usuario(
            tenant_id=tenant.id, nombre="Profe", apellidos="A",
            email_encrypted="enc-prof", email_hash="hash-prof-lc", facturador=False,
        )
        usuario_fact = Usuario(
            tenant_id=tenant.id, nombre="Fact", apellidos="B",
            email_encrypted="enc-fact", email_hash="hash-fact-lc", facturador=True,
        )
        sal_base = SalarioBase(
            tenant_id=tenant.id, rol="PROFESOR", monto=Decimal("5000"), desde=date(2026, 1, 1),
        )
        sal_plus = SalarioPlus(
            tenant_id=tenant.id, grupo="PROG", rol="PROFESOR", monto=Decimal("800"), desde=date(2026, 1, 1),
        )
        s.add_all([cohorte, mat_prog, mat_prog2, mat_mate, usuario_prof, usuario_fact, sal_base, sal_plus])
        await s.flush()
        await s.commit()

    app = FastAPI()
    app.include_router(liq_router)

    return {
        "app": app,
        "sf": sf,
        "tok_fin": _tok(auth_fin.id, tenant.id, ["FINANZAS"]),
        "tenant_id": tenant.id,
        "cohorte_id": cohorte.id,
        "rol_prof_id": rol_prof.id,
        "usuario_prof_id": usuario_prof.id,
        "usuario_fact_id": usuario_fact.id,
        "mat_prog_id": mat_prog.id,
        "mat_prog2_id": mat_prog2.id,
        "mat_mate_id": mat_mate.id,
    }


async def _add_asignacion(sf, **kwargs) -> None:
    async with sf() as s:
        s.add(Asignacion(**kwargs, comisiones=[], desde=date(2026, 1, 1)))
        await s.commit()


async def _calcular(ctx) -> tuple[int, list]:
    async with AsyncClient(transport=ASGITransport(app=ctx["app"]), base_url="http://test") as cli:
        r = await cli.post(
            "/api/liquidaciones/calcular",
            json={"cohorte_id": str(ctx["cohorte_id"]), "periodo": "2026-01"},
            headers=_auth(ctx["tok_fin"]),
        )
    return r.status_code, r.json()


# ---------------------------------------------------------------------------
# RED → GREEN: cálculo correcto con 1 comisión
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculo_1_comision_total_correcto(ctx):
    """RED→GREEN: 1 comisión PROG → total = base(5000) + plus(800) = 5800."""
    c = ctx
    await _add_asignacion(
        c["sf"],
        tenant_id=c["tenant_id"],
        usuario_id=c["usuario_prof_id"],
        rol_id=c["rol_prof_id"],
        materia_id=c["mat_prog_id"],
        cohorte_id=c["cohorte_id"],
    )

    status, data = await _calcular(c)
    assert status == 201
    assert len(data) == 1
    row = data[0]
    assert Decimal(row["monto_base"]) == Decimal("5000")
    assert Decimal(row["monto_plus"]) == Decimal("800")
    assert Decimal(row["total"]) == Decimal("5800")
    assert row["es_nexo"] is False
    assert row["excluido_por_factura"] is False


# ---------------------------------------------------------------------------
# TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculo_n_comisiones_acumula_plus(ctx):
    """TRIANGULATE: 2 materias con categoria PROG → plus = 2 × 800 = 1600."""
    c = ctx
    for mat_id in (c["mat_prog_id"], c["mat_prog2_id"]):
        await _add_asignacion(
            c["sf"],
            tenant_id=c["tenant_id"],
            usuario_id=c["usuario_prof_id"],
            rol_id=c["rol_prof_id"],
            materia_id=mat_id,
            cohorte_id=c["cohorte_id"],
        )

    status, data = await _calcular(c)
    assert status == 201
    row = next(r for r in data if str(r["usuario_id"]) == str(c["usuario_prof_id"]))
    assert Decimal(row["monto_plus"]) == Decimal("1600")
    assert Decimal(row["total"]) == Decimal("6600")


@pytest.mark.asyncio
async def test_calculo_materia_sin_categoria_no_suma_plus(ctx):
    """TRIANGULATE: materia con categoria_plus=None → plus=0."""
    c = ctx
    await _add_asignacion(
        c["sf"],
        tenant_id=c["tenant_id"],
        usuario_id=c["usuario_prof_id"],
        rol_id=c["rol_prof_id"],
        materia_id=c["mat_mate_id"],
        cohorte_id=c["cohorte_id"],
    )

    status, data = await _calcular(c)
    assert status == 201
    row = data[0]
    assert Decimal(row["monto_plus"]) == Decimal("0")
    assert Decimal(row["total"]) == Decimal("5000")


@pytest.mark.asyncio
async def test_calculo_facturador_marcado_excluido(ctx):
    """TRIANGULATE: usuario con facturador=True → excluido_por_factura=True."""
    c = ctx
    await _add_asignacion(
        c["sf"],
        tenant_id=c["tenant_id"],
        usuario_id=c["usuario_fact_id"],
        rol_id=c["rol_prof_id"],
        materia_id=c["mat_prog_id"],
        cohorte_id=c["cohorte_id"],
    )

    status, data = await _calcular(c)
    assert status == 201
    row = next(r for r in data if str(r["usuario_id"]) == str(c["usuario_fact_id"]))
    assert row["excluido_por_factura"] is True


@pytest.mark.asyncio
async def test_calculo_idempotente_no_duplica_filas(ctx):
    """TRIANGULATE: recalcular período abierto → mismo id, misma data (upsert)."""
    c = ctx
    await _add_asignacion(
        c["sf"],
        tenant_id=c["tenant_id"],
        usuario_id=c["usuario_prof_id"],
        rol_id=c["rol_prof_id"],
        materia_id=c["mat_prog_id"],
        cohorte_id=c["cohorte_id"],
    )

    _, data1 = await _calcular(c)
    _, data2 = await _calcular(c)
    assert len(data1) == 1
    assert len(data2) == 1
    assert data1[0]["id"] == data2[0]["id"]
    assert data1[0]["total"] == data2[0]["total"]


@pytest.mark.asyncio
async def test_calcular_periodo_cerrado_409(ctx):
    """TRIANGULATE: calcular sobre período ya cerrado → 409."""
    c = ctx
    await _add_asignacion(
        c["sf"],
        tenant_id=c["tenant_id"],
        usuario_id=c["usuario_prof_id"],
        rol_id=c["rol_prof_id"],
        materia_id=c["mat_prog_id"],
        cohorte_id=c["cohorte_id"],
    )

    await _calcular(c)

    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        await cli.post(
            f"/api/liquidaciones/{c['cohorte_id']}/2026-01/cerrar",
            headers=_auth(c["tok_fin"]),
        )
        r = await cli.post(
            "/api/liquidaciones/calcular",
            json={"cohorte_id": str(c["cohorte_id"]), "periodo": "2026-01"},
            headers=_auth(c["tok_fin"]),
        )
    assert r.status_code == 409
