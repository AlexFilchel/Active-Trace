"""Tests C-17 — task 6.3: fragmento LMS."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import (
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
    """Tenant A con materia, cohorte, fechas pre-cargadas. Tenant B vacío de fechas."""
    from app.api.v1.routers.programas import fechas_router

    await ensure_schema()
    sf = get_session_factory()

    async with sf() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant LmsA", slug="lms-a")
        tenant_b = Tenant(name="Tenant LmsB", slug="lms-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@lms-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@lms-b.local",
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

        carrera = Carrera(tenant_id=tenant_a.id, codigo="CRR-L", nombre="Carrera LMS")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRR-LB", nombre="Carrera LMS B")
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
        materia = Materia(tenant_id=tenant_a.id, codigo="MAT-L", nombre="Programación I")
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-LB", nombre="Programación B")
        session.add_all([cohorte, cohorte_b, materia, materia_b])
        await session.flush()

        u_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="L",
            email_encrypted="enc-cl", email_hash="hash-cl",
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

        # Pre-load fechas for tenant A in periodo 2026-1
        session.add_all([
            FechaAcademica(
                tenant_id=tenant_a.id, materia_id=materia.id, cohorte_id=cohorte.id,
                tipo="Parcial", numero=1, periodo="2026-1",
                fecha=date(2026, 4, 15), titulo="Primer Parcial",
            ),
            FechaAcademica(
                tenant_id=tenant_a.id, materia_id=materia.id, cohorte_id=cohorte.id,
                tipo="TP", numero=1, periodo="2026-1",
                fecha=date(2026, 3, 20), titulo="TP Práctico",
            ),
        ])
        await session.commit()

    app = FastAPI()
    app.include_router(fechas_router)

    return {
        "app": app,
        "materia": materia,
        "materia_b": materia_b,
        "cohorte": cohorte,
        "cohorte_b": cohorte_b,
        "tok_coord": _tok(auth_coord.id, tenant_a.id, ["COORDINADOR"]),
        "tok_coord_b": _tok(auth_coord_b.id, tenant_b.id, ["COORDINADOR"]),
    }


# ---------------------------------------------------------------------------
# 6.3 RED→GREEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fragmento_con_fechas_retorna_texto_formateado(ctx):
    """RED→GREEN: GET /fragmento-lms con fechas → texto no vacío con formato markdown."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            "/api/fechas-academicas/fragmento-lms",
            params={
                "materia_id": str(c["materia"].id),
                "cohorte_id": str(c["cohorte"].id),
                "periodo": "2026-1",
            },
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 200
    body = r.json()
    texto = body["texto"]
    assert texto != ""
    assert "Programación I" in texto
    assert "2026-1" in texto
    # Fechas deben aparecer en formato DD/MM/YYYY
    assert "15/04/2026" in texto
    assert "20/03/2026" in texto
    # Ordenadas por fecha ASC (TP antes de Parcial)
    assert texto.index("20/03/2026") < texto.index("15/04/2026")


@pytest.mark.asyncio
async def test_fragmento_sin_fechas_retorna_texto_vacio(ctx):
    """Sin fechas en el período → {"texto": ""}."""
    c = ctx
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            "/api/fechas-academicas/fragmento-lms",
            params={
                "materia_id": str(c["materia"].id),
                "cohorte_id": str(c["cohorte"].id),
                "periodo": "2099-1",
            },
            headers=_auth(c["tok_coord"]),
        )
    assert r.status_code == 200
    assert r.json() == {"texto": ""}


# ---------------------------------------------------------------------------
# 6.3 TRIANGULATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aislamiento_tenant_en_fragmento(ctx):
    """TRIANGULATE: coord de tenant B no ve fechas de tenant A en el fragmento."""
    c = ctx
    # Tenant B hace consulta con los IDs de materia/cohorte de tenant A (cross-tenant attack)
    async with AsyncClient(transport=ASGITransport(app=c["app"]), base_url="http://test") as cli:
        r = await cli.get(
            "/api/fechas-academicas/fragmento-lms",
            params={
                "materia_id": str(c["materia"].id),
                "cohorte_id": str(c["cohorte"].id),
                "periodo": "2026-1",
            },
            headers=_auth(c["tok_coord_b"]),
        )
    assert r.status_code == 200
    # Tenant B no tiene fechas para esos IDs → texto vacío
    assert r.json()["texto"] == ""
