"""Tests for C-13 encuentros y guardias.

TDD Cycle:
  Safety Net → RED (write failing test) → GREEN (minimal impl) → TRIANGULATE → REFACTOR

The suite requires a running PostgreSQL on localhost:5432 (activia_trace_test).
"""
from __future__ import annotations

from datetime import date, time, timedelta
import uuid

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
from app.models.encuentros import InstanciaEncuentro, SlotEncuentro, Guardia
from app.models.usuarios import Asignacion
from tests.usuarios_test_utils import clean_database, ensure_schema


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def ctx(valid_env):
    """Fixture: two tenants, two roles, two permission sets, shared infra."""
    from app.api.v1.routers.encuentros import router as encuentros_router
    from app.api.v1.routers.guardias import router as guardias_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant A", slug="enc-a")
        tenant_b = Tenant(name="Tenant B", slug="enc-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        # --- Auth users ---
        auth_prof = AuthUser(
            tenant_id=tenant_a.id, email="prof@a.local",
            password_hash=hash_password("P1!"), roles=["PROFESOR"]
        )
        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"]
        )
        auth_forbidden = AuthUser(
            tenant_id=tenant_a.id, email="forbidden@a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"]
        )
        auth_b = AuthUser(
            tenant_id=tenant_b.id, email="prof@b.local",
            password_hash=hash_password("P1!"), roles=["PROFESOR"]
        )
        session.add_all([auth_prof, auth_coord, auth_forbidden, auth_b])
        await session.flush()

        # --- Roles ---
        rol_prof = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        rol_coord = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_alumno = Rol(tenant_id=tenant_a.id, nombre="ALUMNO")
        rol_prof_b = Rol(tenant_id=tenant_b.id, nombre="PROFESOR")
        session.add_all([rol_prof, rol_coord, rol_alumno, rol_prof_b])
        await session.flush()

        # --- Permissions ---
        perm_gestionar = Permiso(tenant_id=tenant_a.id, nombre="encuentros:gestionar")
        perm_guardia = Permiso(tenant_id=tenant_a.id, nombre="guardias:registrar")
        perm_gestionar_b = Permiso(tenant_id=tenant_b.id, nombre="encuentros:gestionar")
        perm_guardia_b = Permiso(tenant_id=tenant_b.id, nombre="guardias:registrar")
        session.add_all([perm_gestionar, perm_guardia, perm_gestionar_b, perm_guardia_b])
        await session.flush()

        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_prof.id, permiso_id=perm_gestionar.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_prof.id, permiso_id=perm_guardia.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=perm_gestionar.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=perm_guardia.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_prof_b.id, permiso_id=perm_gestionar_b.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_prof_b.id, permiso_id=perm_guardia_b.id),
        ])

        # --- Estructura ---
        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CAR-A", nombre="Carrera A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CAR-B", nombre="Carrera B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera_a.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1)
        )
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-A", nombre="Materia A")
        cohorte_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=carrera_b.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1)
        )
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
        session.add_all([cohorte_a, materia_a, cohorte_b, materia_b])
        await session.flush()

        # --- Usuarios ---
        usuario_prof = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_prof.id,
            nombre="Prof", apellidos="A",
            email_encrypted="enc-prof-a", email_hash="hash-prof-a",
        )
        usuario_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="A",
            email_encrypted="enc-coord-a", email_hash="hash-coord-a",
        )
        usuario_b = Usuario(
            tenant_id=tenant_b.id, auth_user_id=auth_b.id,
            nombre="Prof", apellidos="B",
            email_encrypted="enc-prof-b", email_hash="hash-prof-b",
        )
        session.add_all([usuario_prof, usuario_coord, usuario_b])
        await session.flush()

        # --- Asignaciones ---
        asig_a = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_prof.id,
            rol_id=rol_prof.id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            desde=date(2026, 1, 1),
        )
        asig_b = Asignacion(
            tenant_id=tenant_b.id,
            usuario_id=usuario_b.id,
            rol_id=rol_prof_b.id,
            materia_id=materia_b.id,
            carrera_id=carrera_b.id,
            cohorte_id=cohorte_b.id,
            desde=date(2026, 1, 1),
        )
        session.add_all([asig_a, asig_b])
        await session.commit()

        # --- Tokens ---
        token_prof = create_access_token(
            user_id=str(auth_prof.id), tenant_id=str(tenant_a.id), roles=["PROFESOR"]
        )
        token_coord = create_access_token(
            user_id=str(auth_coord.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"]
        )
        token_forbidden = create_access_token(
            user_id=str(auth_forbidden.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"]
        )
        token_b = create_access_token(
            user_id=str(auth_b.id), tenant_id=str(tenant_b.id), roles=["PROFESOR"]
        )

        app = FastAPI()
        app.include_router(encuentros_router)
        app.include_router(guardias_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield {
                "client": client,
                "session": session,
                "tenant_a_id": tenant_a.id,
                "tenant_b_id": tenant_b.id,
                "materia_a_id": materia_a.id,
                "materia_b_id": materia_b.id,
                "carrera_a_id": carrera_a.id,
                "cohorte_a_id": cohorte_a.id,
                "asig_a_id": asig_a.id,
                "asig_b_id": asig_b.id,
                "token_prof": token_prof,
                "token_coord": token_coord,
                "token_forbidden": token_forbidden,
                "token_b": token_b,
            }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _h(ctx: dict, role: str = "prof") -> dict:
    token_key = f"token_{role}"
    return {"Authorization": f"Bearer {ctx[token_key]}"}


# ---------------------------------------------------------------------------
# 7.1 — Generación recurrente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recurrente_8_semanas_crea_slot_y_8_instancias(ctx):
    """RED→GREEN: cant_semanas=8 must create exactly 1 slot + 8 instancias."""
    # fecha_inicio must fall on dia_semana (Monday=0)
    fecha_inicio = date(2026, 6, 15)  # Monday
    assert fecha_inicio.weekday() == 0

    response = await ctx["client"].post(
        "/api/encuentros/recurrente",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "dia_semana": 0,
            "hora": "18:00:00",
            "fecha_inicio": str(fecha_inicio),
            "cant_semanas": 8,
            "titulo": "Clase semanal",
            "meet_url": "https://meet.google.com/test",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["instancias_creadas"] == 8
    assert body["slot"]["cant_semanas"] == 8

    # Verify in DB
    from sqlalchemy import select
    session = ctx["session"]
    slot_rows = (await session.scalars(
        select(SlotEncuentro).where(SlotEncuentro.tenant_id == ctx["tenant_a_id"])
    )).all()
    assert len(slot_rows) == 1

    inst_rows = (await session.scalars(
        select(InstanciaEncuentro).where(InstanciaEncuentro.tenant_id == ctx["tenant_a_id"])
    )).all()
    assert len(inst_rows) == 8

    # Dates are fecha_inicio + 7*k
    fechas = sorted(i.fecha for i in inst_rows)
    for k, f in enumerate(fechas):
        assert f == fecha_inicio + timedelta(weeks=k)


@pytest.mark.asyncio
async def test_recurrente_triangula_1_semana_crea_1_instancia(ctx):
    """TRIANGULATE: cant_semanas=1 creates exactly 1 instancia."""
    fecha_inicio = date(2026, 6, 15)  # Monday

    response = await ctx["client"].post(
        "/api/encuentros/recurrente",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "dia_semana": 0,
            "hora": "19:00:00",
            "fecha_inicio": str(fecha_inicio),
            "cant_semanas": 1,
            "titulo": "Clase única recurrente",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 201
    assert response.json()["instancias_creadas"] == 1


@pytest.mark.asyncio
async def test_recurrente_fecha_inicio_incoherente_con_dia_semana_retorna_422(ctx):
    """SPEC: fecha_inicio that doesn't match dia_semana → 422."""
    fecha_inicio = date(2026, 6, 16)  # Tuesday
    assert fecha_inicio.weekday() == 1

    response = await ctx["client"].post(
        "/api/encuentros/recurrente",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "dia_semana": 0,  # Monday — mismatch
            "hora": "18:00:00",
            "fecha_inicio": str(fecha_inicio),
            "cant_semanas": 4,
            "titulo": "Clase con fecha incorrecta",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recurrente_sin_permiso_retorna_403(ctx):
    """SPEC: no permission → 403, nothing created."""
    fecha_inicio = date(2026, 6, 15)
    response = await ctx["client"].post(
        "/api/encuentros/recurrente",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "dia_semana": 0,
            "hora": "18:00:00",
            "fecha_inicio": str(fecha_inicio),
            "cant_semanas": 4,
            "titulo": "No pasa",
        },
        headers=_h(ctx, "forbidden"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_recurrente_audit_log_registrado(ctx):
    """SPEC: AuditLog with accion=ENCUENTRO_GESTIONAR and filas_afectadas=8."""
    from sqlalchemy import select

    fecha_inicio = date(2026, 6, 15)
    response = await ctx["client"].post(
        "/api/encuentros/recurrente",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "dia_semana": 0,
            "hora": "18:00:00",
            "fecha_inicio": str(fecha_inicio),
            "cant_semanas": 8,
            "titulo": "Clase auditada",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 201

    session = ctx["session"]
    audit = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx["tenant_a_id"])
        .where(AuditLog.accion == "ENCUENTRO_GESTIONAR")
    )
    assert audit is not None
    assert audit.filas_afectadas == 8


# ---------------------------------------------------------------------------
# 7.2 — Encuentro único
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unico_crea_slot_cant_semanas_0_y_una_instancia(ctx):
    """SPEC: unico creates slot (cant_semanas=0) + exactly 1 instancia."""
    fecha = date(2026, 6, 20)

    response = await ctx["client"].post(
        "/api/encuentros/unico",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "fecha": str(fecha),
            "hora": "17:00:00",
            "titulo": "Clase puntual",
            "meet_url": "https://meet.google.com/puntual",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["slot"]["cant_semanas"] == 0
    assert body["instancia"]["estado"] == "Programado"
    assert body["instancia"]["fecha"] == str(fecha)


@pytest.mark.asyncio
async def test_unico_triangula_instancia_en_fecha_correcta(ctx):
    """TRIANGULATE: the instancia is in the exact fecha specified."""
    fecha = date(2026, 7, 4)

    response = await ctx["client"].post(
        "/api/encuentros/unico",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "fecha": str(fecha),
            "hora": "10:00:00",
            "titulo": "Clase extra julio",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 201
    assert response.json()["instancia"]["fecha"] == str(fecha)


# ---------------------------------------------------------------------------
# 7.3 — Editar instancia
# ---------------------------------------------------------------------------

async def _crear_instancia(ctx: dict) -> str:
    """Helper: create one encounter and return its instancia id."""
    fecha = date(2026, 6, 20)
    r = await ctx["client"].post(
        "/api/encuentros/unico",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "fecha": str(fecha),
            "hora": "15:00:00",
            "titulo": "Para editar",
        },
        headers=_h(ctx),
    )
    assert r.status_code == 201
    return r.json()["instancia"]["id"]


@pytest.mark.asyncio
async def test_editar_instancia_realizado_con_video_url(ctx):
    """SPEC: PATCH estado=Realizado + video_url persists."""
    instancia_id = await _crear_instancia(ctx)

    response = await ctx["client"].patch(
        f"/api/encuentros/instancias/{instancia_id}",
        json={"estado": "Realizado", "video_url": "https://youtube.com/abc"},
        headers=_h(ctx),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["estado"] == "Realizado"
    assert body["video_url"] == "https://youtube.com/abc"


@pytest.mark.asyncio
async def test_editar_instancia_cancelado(ctx):
    """TRIANGULATE: PATCH estado=Cancelado persists."""
    instancia_id = await _crear_instancia(ctx)

    response = await ctx["client"].patch(
        f"/api/encuentros/instancias/{instancia_id}",
        json={"estado": "Cancelado"},
        headers=_h(ctx),
    )
    assert response.status_code == 200
    assert response.json()["estado"] == "Cancelado"


@pytest.mark.asyncio
async def test_editar_instancia_campo_extra_retorna_422(ctx):
    """SPEC: extra='forbid' rejects unknown field 'fecha'."""
    instancia_id = await _crear_instancia(ctx)

    response = await ctx["client"].patch(
        f"/api/encuentros/instancias/{instancia_id}",
        json={"estado": "Realizado", "fecha": "2026-01-01"},
        headers=_h(ctx),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_editar_instancia_inexistente_retorna_404(ctx):
    """SPEC: unknown instancia_id → 404."""
    fake_id = uuid.uuid4()
    response = await ctx["client"].patch(
        f"/api/encuentros/instancias/{fake_id}",
        json={"estado": "Realizado"},
        headers=_h(ctx),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7.4 — Bloque HTML
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bloque_html_con_instancias_retorna_tabla(ctx):
    """SPEC: with instancias, returns HTML with rows and escaped links."""
    # Create one encounter
    fecha = date(2026, 6, 20)
    await ctx["client"].post(
        "/api/encuentros/unico",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "asignacion_id": str(ctx["asig_a_id"]),
            "fecha": str(fecha),
            "hora": "14:00:00",
            "titulo": "Clase con <b>HTML</b>",
            "meet_url": "https://meet.google.com/abc",
        },
        headers=_h(ctx),
    )

    response = await ctx["client"].get(
        f"/api/encuentros/bloque-html?materia_id={ctx['materia_a_id']}",
        headers=_h(ctx),
    )
    assert response.status_code == 200
    body = response.json()
    assert "html" in body
    html_str = body["html"]
    assert "<table>" in html_str
    assert "<tbody>" in html_str
    # Content is HTML-escaped: < becomes &lt;
    assert "&lt;b&gt;" in html_str or "Clase con" in html_str
    assert "meet.google.com" in html_str


@pytest.mark.asyncio
async def test_bloque_html_sin_instancias_retorna_tabla_vacia_200(ctx):
    """SPEC: no instancias for the materia → empty tbody, status 200."""
    response = await ctx["client"].get(
        f"/api/encuentros/bloque-html?materia_id={ctx['materia_a_id']}",
        headers=_h(ctx),
    )
    assert response.status_code == 200
    body = response.json()
    html_str = body["html"]
    assert "<tbody></tbody>" in html_str


# ---------------------------------------------------------------------------
# 7.5 — Vista admin GET /api/encuentros
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_ve_todos_los_encuentros_del_tenant(ctx):
    """SPEC: admin listing returns all instancias in the tenant."""
    # Prof creates 2 encuentros
    fecha1 = date(2026, 6, 20)
    fecha2 = date(2026, 6, 21)
    for f, h in [(fecha1, "10:00:00"), (fecha2, "11:00:00")]:
        await ctx["client"].post(
            "/api/encuentros/unico",
            json={
                "materia_id": str(ctx["materia_a_id"]),
                "asignacion_id": str(ctx["asig_a_id"]),
                "fecha": str(f),
                "hora": h,
                "titulo": "Encuentro",
            },
            headers=_h(ctx),
        )

    # Coord lists all
    response = await ctx["client"].get("/api/encuentros", headers=_h(ctx, "coord"))
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_admin_filtro_estado_realizado(ctx):
    """SPEC: filter estado=Realizado returns only those."""
    # Create two instancias
    fecha1, fecha2 = date(2026, 6, 20), date(2026, 6, 21)
    ids = []
    for f in [fecha1, fecha2]:
        r = await ctx["client"].post(
            "/api/encuentros/unico",
            json={
                "materia_id": str(ctx["materia_a_id"]),
                "asignacion_id": str(ctx["asig_a_id"]),
                "fecha": str(f),
                "hora": "09:00:00",
                "titulo": "Para filtrar",
            },
            headers=_h(ctx),
        )
        ids.append(r.json()["instancia"]["id"])

    # Mark first as Realizado
    await ctx["client"].patch(
        f"/api/encuentros/instancias/{ids[0]}",
        json={"estado": "Realizado"},
        headers=_h(ctx),
    )

    response = await ctx["client"].get("/api/encuentros?estado=Realizado", headers=_h(ctx))
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["estado"] == "Realizado"


@pytest.mark.asyncio
async def test_tenant_isolation_encuentros(ctx):
    """SPEC: instancias from tenant_b don't appear when tenant_a lists."""
    # Tenant B creates an encuentro
    await ctx["client"].post(
        "/api/encuentros/unico",
        json={
            "materia_id": str(ctx["materia_b_id"]),
            "asignacion_id": str(ctx["asig_b_id"]),
            "fecha": str(date(2026, 6, 20)),
            "hora": "08:00:00",
            "titulo": "Encuentro tenant B",
        },
        headers=_h(ctx, "b"),
    )

    # Tenant A sees nothing
    response = await ctx["client"].get("/api/encuentros", headers=_h(ctx))
    assert response.status_code == 200
    assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# 7.6 — Registrar guardia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registrar_guardia_crea_en_pendiente(ctx):
    """SPEC: POST /api/guardias returns 201, estado=Pendiente."""
    response = await ctx["client"].post(
        "/api/guardias",
        json={
            "asignacion_id": str(ctx["asig_a_id"]),
            "materia_id": str(ctx["materia_a_id"]),
            "carrera_id": str(ctx["carrera_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "dia": "2026-06-20",
            "horario": "10:00-12:00",
            "comentarios": "Guardia de prueba",
        },
        headers=_h(ctx),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["estado"] == "Pendiente"
    assert body["horario"] == "10:00-12:00"


@pytest.mark.asyncio
async def test_registrar_guardia_audit_log(ctx):
    """SPEC: AuditLog with accion=GUARDIA_REGISTRAR is created."""
    from sqlalchemy import select

    await ctx["client"].post(
        "/api/guardias",
        json={
            "asignacion_id": str(ctx["asig_a_id"]),
            "materia_id": str(ctx["materia_a_id"]),
            "carrera_id": str(ctx["carrera_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "dia": "2026-06-21",
            "horario": "14:00-16:00",
        },
        headers=_h(ctx),
    )

    session = ctx["session"]
    audit = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx["tenant_a_id"])
        .where(AuditLog.accion == "GUARDIA_REGISTRAR")
    )
    assert audit is not None


@pytest.mark.asyncio
async def test_registrar_guardia_asignacion_otro_tenant_retorna_404(ctx):
    """SPEC: asignacion_id from tenant_b → 404 in tenant_a."""
    response = await ctx["client"].post(
        "/api/guardias",
        json={
            "asignacion_id": str(ctx["asig_b_id"]),  # belongs to tenant_b
            "materia_id": str(ctx["materia_a_id"]),
            "carrera_id": str(ctx["carrera_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "dia": "2026-06-22",
            "horario": "09:00-11:00",
        },
        headers=_h(ctx),  # tenant_a token
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_registrar_guardia_sin_permiso_retorna_403(ctx):
    """SPEC: ALUMNO (no guardias:registrar) → 403."""
    response = await ctx["client"].post(
        "/api/guardias",
        json={
            "asignacion_id": str(ctx["asig_a_id"]),
            "materia_id": str(ctx["materia_a_id"]),
            "carrera_id": str(ctx["carrera_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "dia": "2026-06-23",
            "horario": "09:00-11:00",
        },
        headers=_h(ctx, "forbidden"),
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 7.7 — Consulta y exportación de guardias
# ---------------------------------------------------------------------------

async def _crear_guardia(ctx: dict, dia: str = "2026-06-20") -> dict:
    r = await ctx["client"].post(
        "/api/guardias",
        json={
            "asignacion_id": str(ctx["asig_a_id"]),
            "materia_id": str(ctx["materia_a_id"]),
            "carrera_id": str(ctx["carrera_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "dia": dia,
            "horario": "10:00-12:00",
        },
        headers=_h(ctx),
    )
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_listar_guardias_filtro_materia(ctx):
    """SPEC: filter materia_id returns only matching guardias."""
    # Create 2 guardias
    await _crear_guardia(ctx, "2026-06-20")
    await _crear_guardia(ctx, "2026-06-21")

    # Filter by materia_a — should return both
    response = await ctx["client"].get(
        f"/api/guardias?materia_id={ctx['materia_a_id']}",
        headers=_h(ctx),
    )
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Filter by a random materia — should return 0
    response2 = await ctx["client"].get(
        f"/api/guardias?materia_id={uuid.uuid4()}",
        headers=_h(ctx),
    )
    assert response2.status_code == 200
    assert len(response2.json()) == 0


@pytest.mark.asyncio
async def test_exportar_guardias_retorna_csv_con_headers_y_filas(ctx):
    """SPEC: GET /api/guardias/exportar returns CSV with headers + rows."""
    await _crear_guardia(ctx, "2026-06-20")

    response = await ctx["client"].get("/api/guardias/exportar", headers=_h(ctx))
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    content = response.text
    lines = [l for l in content.strip().split("\n") if l]
    assert lines[0].startswith("usuario_id")
    assert len(lines) == 2  # header + 1 data row


@pytest.mark.asyncio
async def test_exportar_sin_guardias_retorna_csv_solo_headers(ctx):
    """SPEC: no guardias → CSV with only headers, status 200."""
    response = await ctx["client"].get("/api/guardias/exportar", headers=_h(ctx))
    assert response.status_code == 200

    content = response.text
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # only the header row
    assert lines[0].startswith("usuario_id")
