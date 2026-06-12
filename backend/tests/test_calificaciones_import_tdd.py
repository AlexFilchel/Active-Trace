"""TDD: calificaciones — preview, importar, vaciado, tenant isolation."""
from __future__ import annotations

import hashlib
import hmac
import io
import uuid
from datetime import date

import openpyxl
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
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
)
from app.models.calificacion import Calificacion
from app.models.padron import EntradaPadron, VersionPadron
from app.models.usuarios import Asignacion, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


def _make_lms_xlsx(
    alumnos: list[dict],
    actividades_numericas: list[str] | None = None,
    actividades_textuales: list[str] | None = None,
) -> bytes:
    """Build a Moodle-style gradebook xlsx file."""
    actividades_numericas = actividades_numericas or []
    actividades_textuales = actividades_textuales or []
    headers = ["Nombre", "Apellidos", "Dirección de correo"] + actividades_numericas + actividades_textuales

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for alumno in alumnos:
        row = [
            alumno.get("nombre", ""),
            alumno.get("apellidos", ""),
            alumno.get("email", ""),
        ]
        for act in actividades_numericas:
            row.append(alumno.get(act, ""))
        for act in actividades_textuales:
            row.append(alumno.get(act, ""))
        ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _hash_email(email: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
async def calificaciones_app(valid_env):
    from app.api.v1.routers.calificaciones import router as cal_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Cal Tenant A", slug="cal-a")
        tenant_b = Tenant(name="Cal Tenant B", slug="cal-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        # Auth users
        auth_a = AuthUser(tenant_id=tenant_a.id, email="prof@cal-a.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        auth_b = AuthUser(tenant_id=tenant_b.id, email="prof@cal-b.local", password_hash=hash_password("P1!"), roles=["PROFESOR"])
        session.add_all([auth_a, auth_b])
        await session.flush()

        # RBAC
        rol_a = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        permiso_a = Permiso(tenant_id=tenant_a.id, nombre="calificaciones:importar")
        session.add_all([rol_a, permiso_a])
        await session.flush()
        session.add(RolPermiso(tenant_id=tenant_a.id, rol_id=rol_a.id, permiso_id=permiso_a.id))

        # Estructura
        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CAR-C", nombre="Carrera Cal")
        session.add(carrera_a)
        await session.flush()
        cohorte_a = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera_a.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-C", nombre="Materia Cal")
        session.add_all([cohorte_a, materia_a])
        await session.flush()

        # Usuarios y asignaciones docentes
        usuario_a = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=auth_a.id,
            nombre="Profesor",
            apellidos="A",
            email_encrypted="enc-prof-a",
            email_hash=_hash_email("prof@cal-a.local"),
        )
        usuario_b_tenant_a = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=None,
            nombre="Profesor",
            apellidos="B_en_A",
            email_encrypted="enc-prof-b-a",
            email_hash=_hash_email("profb@cal-a.local"),
        )
        session.add_all([usuario_a, usuario_b_tenant_a])
        await session.flush()

        asignacion_a = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_a.id,
            rol_id=rol_a.id,
            materia_id=materia_a.id,
            desde=date(2026, 1, 1),
        )
        session.add(asignacion_a)
        await session.flush()

        # Padrón activo con 2 alumnos
        version = VersionPadron(
            tenant_id=tenant_a.id,
            materia_id=materia_a.id,
            cohorte_id=cohorte_a.id,
            cargado_por=usuario_a.id,
            activa=True,
        )
        session.add(version)
        await session.flush()

        alumno1_email = "alumno1@test.com"
        alumno2_email = "alumno2@test.com"

        entrada1 = EntradaPadron(
            tenant_id=tenant_a.id,
            version_id=version.id,
            nombre="Alumno",
            apellidos="Uno",
            email_encrypted="enc-a1",
            email_hash=_hash_email(alumno1_email),
        )
        entrada2 = EntradaPadron(
            tenant_id=tenant_a.id,
            version_id=version.id,
            nombre="Alumno",
            apellidos="Dos",
            email_encrypted="enc-a2",
            email_hash=_hash_email(alumno2_email),
        )
        session.add_all([entrada1, entrada2])
        await session.commit()

        token_a = create_access_token(user_id=str(auth_a.id), tenant_id=str(tenant_a.id), roles=["PROFESOR"])
        token_b = create_access_token(user_id=str(auth_b.id), tenant_id=str(tenant_b.id), roles=["PROFESOR"])

        app = FastAPI()
        app.include_router(cal_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield {
                "client": client,
                "session": session,
                "token_a": token_a,
                "token_b": token_b,
                "tenant_a_id": tenant_a.id,
                "tenant_b_id": tenant_b.id,
                "materia_id": materia_a.id,
                "version_id": version.id,
                "usuario_a_id": usuario_a.id,
                "usuario_b_id": usuario_b_tenant_a.id,
                "alumno1_email": alumno1_email,
                "alumno2_email": alumno2_email,
                "entrada1_id": entrada1.id,
                "entrada2_id": entrada2.id,
            }


# ---------------------------------------------------------------------------
# Preview tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_detecta_columnas_numericas(calificaciones_app):
    ctx = calificaciones_app
    content = _make_lms_xlsx(
        [{"nombre": "Ana", "apellidos": "G", "email": "a@t.com", "Tarea 1 (Real)": "85"}],
        actividades_numericas=["Tarea 1 (Real)"],
    )
    resp = await ctx["client"].post(
        "/api/calificaciones/preview",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Tarea 1 (Real)" in data["actividades_numericas"]
    assert data["actividades_textuales"] == []


@pytest.mark.asyncio
async def test_preview_sin_permiso_retorna_403(calificaciones_app):
    ctx = calificaciones_app
    content = _make_lms_xlsx([])
    resp = await ctx["client"].post(
        "/api/calificaciones/preview",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_b']}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_importar_crea_calificaciones_correctamente(calificaciones_app):
    ctx = calificaciones_app
    alumnos = [
        {"nombre": "Alumno", "apellidos": "Uno", "email": ctx["alumno1_email"], "Tarea 1 (Real)": "85"},
        {"nombre": "Alumno", "apellidos": "Dos", "email": ctx["alumno2_email"], "Tarea 1 (Real)": "70"},
    ]
    content = _make_lms_xlsx(alumnos, actividades_numericas=["Tarea 1 (Real)"])

    materia_id = ctx["materia_id"]
    resp = await ctx["client"].post(
        f"/api/calificaciones/importar?materia_id={materia_id}&actividades=Tarea+1+(Real)",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["calificaciones_importadas"] == 2

    session = ctx["session"]
    from sqlalchemy import select
    result = await session.scalars(select(Calificacion).where(Calificacion.tenant_id == ctx["tenant_a_id"]))
    cals = list(result.all())
    assert len(cals) == 2
    for c in cals:
        assert c.actividad == "Tarea 1 (Real)"
        assert c.nota_numerica is not None
        assert c.aprobado is True  # 85 >= 60 and 70 >= 60


@pytest.mark.asyncio
async def test_importar_aprobado_derivado_numerico(calificaciones_app):
    ctx = calificaciones_app
    alumnos = [
        {"nombre": "Alumno", "apellidos": "Uno", "email": ctx["alumno1_email"], "Quiz (Real)": "55"},
    ]
    content = _make_lms_xlsx(alumnos, actividades_numericas=["Quiz (Real)"])

    materia_id = ctx["materia_id"]
    resp = await ctx["client"].post(
        f"/api/calificaciones/importar?materia_id={materia_id}&actividades=Quiz+(Real)",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 201

    from sqlalchemy import select
    result = await ctx["session"].scalars(
        select(Calificacion)
        .where(Calificacion.tenant_id == ctx["tenant_a_id"])
        .where(Calificacion.actividad == "Quiz (Real)")
    )
    cals = list(result.all())
    assert len(cals) == 1
    assert cals[0].aprobado is False  # 55 < 60


@pytest.mark.asyncio
async def test_importar_aprobado_derivado_textual_aprobatorio(calificaciones_app):
    ctx = calificaciones_app
    alumnos = [
        {"nombre": "Alumno", "apellidos": "Uno", "email": ctx["alumno1_email"], "TP Final": "Satisfactorio"},
    ]
    content = _make_lms_xlsx(alumnos, actividades_textuales=["TP Final"])

    materia_id = ctx["materia_id"]
    resp = await ctx["client"].post(
        f"/api/calificaciones/importar?materia_id={materia_id}&actividades=TP+Final",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 201

    from sqlalchemy import select
    result = await ctx["session"].scalars(
        select(Calificacion)
        .where(Calificacion.tenant_id == ctx["tenant_a_id"])
        .where(Calificacion.actividad == "TP Final")
    )
    cals = list(result.all())
    assert len(cals) == 1
    assert cals[0].aprobado is True


@pytest.mark.asyncio
async def test_importar_aprobado_false_textual_no_aprobatorio(calificaciones_app):
    ctx = calificaciones_app
    alumnos = [
        {"nombre": "Alumno", "apellidos": "Uno", "email": ctx["alumno1_email"], "TP Final": "No satisfactorio"},
    ]
    content = _make_lms_xlsx(alumnos, actividades_textuales=["TP Final"])

    materia_id = ctx["materia_id"]
    resp = await ctx["client"].post(
        f"/api/calificaciones/importar?materia_id={materia_id}&actividades=TP+Final",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 201

    from sqlalchemy import select
    result = await ctx["session"].scalars(
        select(Calificacion)
        .where(Calificacion.tenant_id == ctx["tenant_a_id"])
        .where(Calificacion.actividad == "TP Final")
    )
    cals = list(result.all())
    assert len(cals) == 1
    assert cals[0].aprobado is False


@pytest.mark.asyncio
async def test_importar_audit_registrada(calificaciones_app):
    ctx = calificaciones_app
    alumnos = [{"nombre": "Alumno", "apellidos": "Uno", "email": ctx["alumno1_email"], "Tarea 1 (Real)": "80"}]
    content = _make_lms_xlsx(alumnos, actividades_numericas=["Tarea 1 (Real)"])

    materia_id = ctx["materia_id"]
    await ctx["client"].post(
        f"/api/calificaciones/importar?materia_id={materia_id}&actividades=Tarea+1+(Real)",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )

    from sqlalchemy import select
    result = await ctx["session"].scalars(
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx["tenant_a_id"])
        .where(AuditLog.accion == "CALIFICACIONES_IMPORTAR")
    )
    audits = list(result.all())
    assert len(audits) >= 1


@pytest.mark.asyncio
async def test_importar_tenant_isolation(calificaciones_app):
    """Import by tenant A should not create calificaciones in tenant B scope."""
    ctx = calificaciones_app
    alumnos = [{"nombre": "Alumno", "apellidos": "Uno", "email": ctx["alumno1_email"], "Tarea 1 (Real)": "80"}]
    content = _make_lms_xlsx(alumnos, actividades_numericas=["Tarea 1 (Real)"])

    materia_id = ctx["materia_id"]
    await ctx["client"].post(
        f"/api/calificaciones/importar?materia_id={materia_id}&actividades=Tarea+1+(Real)",
        files={"file": ("notas.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )

    from sqlalchemy import select
    result = await ctx["session"].scalars(
        select(Calificacion).where(Calificacion.tenant_id == ctx["tenant_b_id"])
    )
    assert list(result.all()) == []


# ---------------------------------------------------------------------------
# Vaciado tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vaciado_elimina_solo_calificaciones_del_actor(calificaciones_app):
    """Vaciado removes actor A's calificaciones but not actor B's."""
    ctx = calificaciones_app
    session = ctx["session"]

    # Insert calificaciones for actor A
    cal_a1 = Calificacion(
        tenant_id=ctx["tenant_a_id"],
        entrada_padron_id=ctx["entrada1_id"],
        actor_id=ctx["usuario_a_id"],
        actividad="Tarea 1 (Real)",
        nota_numerica=85,
        aprobado=True,
    )
    # Insert calificaciones for actor B (different usuario in same tenant)
    cal_b1 = Calificacion(
        tenant_id=ctx["tenant_a_id"],
        entrada_padron_id=ctx["entrada1_id"],
        actor_id=ctx["usuario_b_id"],
        actividad="Tarea 1 (Real)",
        nota_numerica=70,
        aprobado=True,
    )
    session.add_all([cal_a1, cal_b1])
    await session.commit()

    materia_id = ctx["materia_id"]
    resp = await ctx["client"].delete(
        f"/api/calificaciones?materia_id={materia_id}",
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eliminadas"] == 1  # only actor A's

    from sqlalchemy import select
    result = await session.scalars(select(Calificacion).where(Calificacion.tenant_id == ctx["tenant_a_id"]))
    remaining = list(result.all())
    assert len(remaining) == 1
    assert remaining[0].actor_id == ctx["usuario_b_id"]


@pytest.mark.asyncio
async def test_vaciado_sin_calificaciones_retorna_cero(calificaciones_app):
    ctx = calificaciones_app
    materia_id = ctx["materia_id"]
    resp = await ctx["client"].delete(
        f"/api/calificaciones?materia_id={materia_id}",
        headers={"Authorization": f"Bearer {ctx['token_a']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["eliminadas"] == 0
