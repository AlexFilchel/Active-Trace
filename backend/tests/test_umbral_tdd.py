"""TDD: umbral de aprobación — GET retorna defecto, PUT persiste, aislamiento por docente."""
from __future__ import annotations

from datetime import date
import hashlib
import hmac

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Carrera, Cohorte, Materia, Permiso, Rol, RolPermiso, Tenant
from app.models.usuarios import Asignacion, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


def _hash_email(email: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
async def umbral_app(valid_env):
    from app.api.v1.routers.calificaciones import router as cal_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant = Tenant(name="Umbral Tenant", slug="umbral-t")
        session.add(tenant)
        await session.flush()

        auth_a = AuthUser(tenant_id=tenant.id, email="prof_a@umbral.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        auth_b = AuthUser(tenant_id=tenant.id, email="prof_b@umbral.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        session.add_all([auth_a, auth_b])
        await session.flush()

        rol = Rol(tenant_id=tenant.id, nombre="PROFESOR")
        permiso = Permiso(tenant_id=tenant.id, nombre="calificaciones:importar")
        session.add_all([rol, permiso])
        await session.flush()
        session.add(RolPermiso(tenant_id=tenant.id, rol_id=rol.id, permiso_id=permiso.id))

        carrera = Carrera(tenant_id=tenant.id, codigo="CAR-U", nombre="Carrera Umbral")
        session.add(carrera)
        await session.flush()
        cohorte = Cohorte(tenant_id=tenant.id, carrera_id=carrera.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia = Materia(tenant_id=tenant.id, codigo="MAT-U", nombre="Materia Umbral")
        session.add_all([cohorte, materia])
        await session.flush()

        usuario_a = Usuario(
            tenant_id=tenant.id,
            auth_user_id=auth_a.id,
            nombre="Prof",
            apellidos="A",
            email_encrypted="enc-a",
            email_hash=_hash_email("prof_a@umbral.local"),
        )
        usuario_b = Usuario(
            tenant_id=tenant.id,
            auth_user_id=auth_b.id,
            nombre="Prof",
            apellidos="B",
            email_encrypted="enc-b",
            email_hash=_hash_email("prof_b@umbral.local"),
        )
        session.add_all([usuario_a, usuario_b])
        await session.flush()

        asig_a = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario_a.id,
            rol_id=rol.id,
            materia_id=materia.id,
            desde=date(2026, 1, 1),
        )
        asig_b = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario_b.id,
            rol_id=rol.id,
            materia_id=materia.id,
            desde=date(2026, 1, 1),
        )
        session.add_all([asig_a, asig_b])
        await session.commit()

        token_a = create_access_token(user_id=str(auth_a.id), tenant_id=str(tenant.id), roles=["PROFESOR"])
        token_b = create_access_token(user_id=str(auth_b.id), tenant_id=str(tenant.id), roles=["PROFESOR"])

        app = FastAPI()
        app.include_router(cal_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield {
                "client": client,
                "token_a": token_a,
                "token_b": token_b,
                "materia_id": materia.id,
            }


@pytest.mark.asyncio
async def test_get_umbral_retorna_defecto_cuando_no_configurado(umbral_app):
    ctx = umbral_app
    resp = await ctx["client"].get(
        f"/api/calificaciones/umbral?materia_id={ctx['materia_id']}",
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["umbral_pct"] == "60"
    assert "Satisfactorio" in data["valores_aprobatorios"]
    assert data["es_defecto"] is True


@pytest.mark.asyncio
async def test_put_umbral_persiste_y_get_retorna_configurado(umbral_app):
    ctx = umbral_app
    payload = {"umbral_pct": "70.00", "valores_aprobatorios": ["Satisfactorio", "Supera lo esperado"]}
    put_resp = await ctx["client"].put(
        f"/api/calificaciones/umbral?materia_id={ctx['materia_id']}",
        json=payload,
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert put_resp.status_code == 200
    put_data = put_resp.json()
    assert put_data["es_defecto"] is False

    get_resp = await ctx["client"].get(
        f"/api/calificaciones/umbral?materia_id={ctx['materia_id']}",
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert float(get_data["umbral_pct"]) == 70.0
    assert get_data["es_defecto"] is False


@pytest.mark.asyncio
async def test_umbral_docente_a_no_afecta_docente_b(umbral_app):
    """Professor A's umbral config does not affect Professor B's GET response."""
    ctx = umbral_app
    payload = {"umbral_pct": "80.00", "valores_aprobatorios": ["Supera lo esperado"]}
    await ctx["client"].put(
        f"/api/calificaciones/umbral?materia_id={ctx['materia_id']}",
        json=payload,
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )

    resp_b = await ctx["client"].get(
        f"/api/calificaciones/umbral?materia_id={ctx['materia_id']}",
        headers={"Authorization": f"Bearer {ctx['token_b']}"},
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["es_defecto"] is True
    assert float(data_b["umbral_pct"]) == 60.0
