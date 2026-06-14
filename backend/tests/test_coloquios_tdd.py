"""Tests for C-14 evaluaciones y coloquios.

TDD Cycle:
  Safety Net → RED (write failing test) → GREEN (minimal impl) → TRIANGULATE → REFACTOR

The suite requires a running PostgreSQL on localhost:5432 (activia_trace_test).

Coverage targets (tasks 6.1–6.8):
  6.1 crear_convocatoria
  6.2 importar_candidatos
  6.3 reservar con cupo
  6.4 sin cupo rechaza
  6.5 reglas de reserva
  6.6 cancelar libera cupo
  6.7 listado / métricas
  6.8 resultados / agenda
"""
from __future__ import annotations

from datetime import date
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
from app.models.usuarios import Asignacion
from tests.usuarios_test_utils import clean_database, ensure_schema


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def ctx(valid_env):
    """Fixture: two tenants, two role sets, alumnos, coordinator.

    KEY DESIGN NOTE:
    The coloquio service uses actor_id_alumno (from JWT user_id) for both:
      - candidato_evaluacion.alumno_id  → FK to usuario.id
      - audit_log.actor_id              → FK to auth_user.id
    To satisfy both FKs with the same UUID, each alumno's AuthUser and Usuario
    are created with the SAME pre-set UUID.
    """
    from app.api.v1.routers.coloquios import router as coloquios_router

    await ensure_schema()
    session_factory = get_session_factory()

    # Pre-set UUIDs so auth_user.id == usuario.id for alumnos
    alumno1_uuid = uuid.uuid4()
    alumno2_uuid = uuid.uuid4()
    alumno3_uuid = uuid.uuid4()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Tenant ColoA", slug="colo-a")
        tenant_b = Tenant(name="Tenant ColoB", slug="colo-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        # --- Auth users ---
        auth_coord = AuthUser(
            tenant_id=tenant_a.id, email="coord@colo-a.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        # Alumnos: id is pre-set so that auth_user.id == usuario.id
        auth_alumno1 = AuthUser(
            id=alumno1_uuid,
            tenant_id=tenant_a.id, email="alumno1@colo-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_alumno2 = AuthUser(
            id=alumno2_uuid,
            tenant_id=tenant_a.id, email="alumno2@colo-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_alumno3 = AuthUser(
            id=alumno3_uuid,
            tenant_id=tenant_a.id, email="alumno3@colo-a.local",
            password_hash=hash_password("P1!"), roles=["ALUMNO"],
        )
        auth_coord_b = AuthUser(
            tenant_id=tenant_b.id, email="coord@colo-b.local",
            password_hash=hash_password("P1!"), roles=["COORDINADOR"],
        )
        session.add_all([auth_coord, auth_alumno1, auth_alumno2, auth_alumno3, auth_coord_b])
        await session.flush()

        # --- Roles ---
        rol_coord = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_alumno = Rol(tenant_id=tenant_a.id, nombre="ALUMNO")
        rol_coord_b = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
        session.add_all([rol_coord, rol_alumno, rol_coord_b])
        await session.flush()

        # --- Permissions ---
        perm_gestionar = Permiso(tenant_id=tenant_a.id, nombre="coloquios:gestionar")
        perm_reservar = Permiso(tenant_id=tenant_a.id, nombre="evaluacion:reservar_instancia")
        perm_gestionar_b = Permiso(tenant_id=tenant_b.id, nombre="coloquios:gestionar")
        session.add_all([perm_gestionar, perm_reservar, perm_gestionar_b])
        await session.flush()

        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=perm_gestionar.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_alumno.id, permiso_id=perm_reservar.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_coord_b.id, permiso_id=perm_gestionar_b.id),
        ])

        # --- Estructura académica ---
        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CRR-A", nombre="Carrera A")
        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CRR-B", nombre="Carrera B")
        session.add_all([carrera_a, carrera_b])
        await session.flush()

        cohorte_a = Cohorte(
            tenant_id=tenant_a.id, carrera_id=carrera_a.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-A", nombre="Materia A")
        cohorte_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=carrera_b.id,
            nombre="2026", anio=2026, vig_desde=date(2026, 1, 1),
        )
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
        session.add_all([cohorte_a, materia_a, cohorte_b, materia_b])
        await session.flush()

        # --- Usuarios ---
        usuario_coord = Usuario(
            tenant_id=tenant_a.id, auth_user_id=auth_coord.id,
            nombre="Coord", apellidos="A",
            email_encrypted="enc-coord-a", email_hash="hash-coord-a",
        )
        # Alumnos: same UUID as their AuthUser (auth_user.id == usuario.id)
        usuario_alumno1 = Usuario(
            id=alumno1_uuid,
            tenant_id=tenant_a.id, auth_user_id=auth_alumno1.id,
            nombre="Alumno", apellidos="Uno",
            email_encrypted="enc-alum1-a", email_hash="hash-alum1-a",
        )
        usuario_alumno2 = Usuario(
            id=alumno2_uuid,
            tenant_id=tenant_a.id, auth_user_id=auth_alumno2.id,
            nombre="Alumno", apellidos="Dos",
            email_encrypted="enc-alum2-a", email_hash="hash-alum2-a",
        )
        usuario_alumno3 = Usuario(
            id=alumno3_uuid,
            tenant_id=tenant_a.id, auth_user_id=auth_alumno3.id,
            nombre="Alumno", apellidos="Tres",
            email_encrypted="enc-alum3-a", email_hash="hash-alum3-a",
        )
        usuario_coord_b = Usuario(
            tenant_id=tenant_b.id, auth_user_id=auth_coord_b.id,
            nombre="Coord", apellidos="B",
            email_encrypted="enc-coord-b", email_hash="hash-coord-b",
        )
        session.add_all([usuario_coord, usuario_alumno1, usuario_alumno2, usuario_alumno3, usuario_coord_b])
        await session.flush()

        # --- Asignaciones ---
        asig_coord = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_coord.id,
            rol_id=rol_coord.id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            desde=date(2026, 1, 1),
        )
        asig_alumno1 = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_alumno1.id,
            rol_id=rol_alumno.id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            desde=date(2026, 1, 1),
        )
        asig_alumno2 = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_alumno2.id,
            rol_id=rol_alumno.id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            desde=date(2026, 1, 1),
        )
        asig_alumno3 = Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario_alumno3.id,
            rol_id=rol_alumno.id,
            materia_id=materia_a.id,
            carrera_id=carrera_a.id,
            cohorte_id=cohorte_a.id,
            desde=date(2026, 1, 1),
        )
        asig_coord_b = Asignacion(
            tenant_id=tenant_b.id,
            usuario_id=usuario_coord_b.id,
            rol_id=rol_coord_b.id,
            materia_id=materia_b.id,
            carrera_id=carrera_b.id,
            cohorte_id=cohorte_b.id,
            desde=date(2026, 1, 1),
        )
        session.add_all([asig_coord, asig_alumno1, asig_alumno2, asig_alumno3, asig_coord_b])
        await session.commit()

        # --- Tokens ---
        token_coord = create_access_token(
            user_id=str(auth_coord.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"],
        )
        token_alumno1 = create_access_token(
            user_id=str(auth_alumno1.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"],
        )
        token_alumno2 = create_access_token(
            user_id=str(auth_alumno2.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"],
        )
        token_alumno3 = create_access_token(
            user_id=str(auth_alumno3.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"],
        )
        token_coord_b = create_access_token(
            user_id=str(auth_coord_b.id), tenant_id=str(tenant_b.id), roles=["COORDINADOR"],
        )

        app = FastAPI()
        app.include_router(coloquios_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield {
                "client": client,
                "session": session,
                "tenant_a_id": tenant_a.id,
                "tenant_b_id": tenant_b.id,
                "materia_a_id": materia_a.id,
                "materia_b_id": materia_b.id,
                "cohorte_a_id": cohorte_a.id,
                "cohorte_b_id": cohorte_b.id,
                # auth user ids (used as JWT user_id / service actor_id)
                "auth_coord_id": auth_coord.id,
                "auth_alumno1_id": auth_alumno1.id,
                "auth_alumno2_id": auth_alumno2.id,
                "auth_alumno3_id": auth_alumno3.id,
                # usuario ids (FK in candidato_evaluacion / reserva_evaluacion / resultado_evaluacion)
                "usuario_coord_id": usuario_coord.id,
                "usuario_alumno1_id": usuario_alumno1.id,
                "usuario_alumno2_id": usuario_alumno2.id,
                "usuario_alumno3_id": usuario_alumno3.id,
                "usuario_coord_b_id": usuario_coord_b.id,
                # tokens
                "token_coord": token_coord,
                "token_alumno1": token_alumno1,
                "token_alumno2": token_alumno2,
                "token_alumno3": token_alumno3,
                "token_coord_b": token_coord_b,
            }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _h(ctx: dict, role: str = "coord") -> dict:
    """Return Authorization header for the given role key."""
    return {"Authorization": f"Bearer {ctx[f'token_{role}']}"}


async def _crear_convocatoria(ctx: dict, dias: list[dict] | None = None) -> dict:
    """Helper: create a convocatoria with 2 days by default. Returns response body."""
    if dias is None:
        dias = [
            {"fecha": "2026-09-10", "cupo_total": 5},
            {"fecha": "2026-09-11", "cupo_total": 3},
        ]
    r = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "instancia": "Primera instancia",
            "dias": dias,
        },
        headers=_h(ctx),
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# 6.1 — Crear convocatoria
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_convocatoria_2_dias_crea_evaluacion_abierta(ctx):
    """RED→GREEN: 2 días → 1 Evaluacion Abierta + 2 DiaEvaluacion."""
    r = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "instancia": "Coloquio 2026-09",
            "dias": [
                {"fecha": "2026-09-10", "cupo_total": 10},
                {"fecha": "2026-09-11", "cupo_total": 5},
            ],
        },
        headers=_h(ctx),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "Abierta"
    assert body["dias_disponibles"] == 2
    assert body["instancia"] == "Coloquio 2026-09"
    # cupos_libres = sum of cupo_total across days
    assert body["cupos_libres"] == 15


@pytest.mark.asyncio
async def test_crear_convocatoria_audit_log_filas_afectadas(ctx):
    """SPEC: audit log COLOQUIO_CREAR with filas_afectadas=2 for 2 días."""
    from sqlalchemy import select

    await _crear_convocatoria(ctx)

    session = ctx["session"]
    audit = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx["tenant_a_id"])
        .where(AuditLog.accion == "COLOQUIO_CREAR")
    )
    assert audit is not None
    assert audit.filas_afectadas == 2


@pytest.mark.asyncio
async def test_crear_convocatoria_triangula_1_dia(ctx):
    """TRIANGULATE: 1 día → dias_disponibles=1 + cupos_libres=cupo del único día."""
    r = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "instancia": "Un solo día",
            "dias": [{"fecha": "2026-09-15", "cupo_total": 7}],
        },
        headers=_h(ctx),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["dias_disponibles"] == 1
    assert body["cupos_libres"] == 7


@pytest.mark.asyncio
async def test_crear_convocatoria_cupo_cero_retorna_422(ctx):
    """SPEC: cupo_total=0 → 422 (schema validation cupo_total > 0)."""
    r = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "instancia": "Cupo cero",
            "dias": [{"fecha": "2026-09-10", "cupo_total": 0}],
        },
        headers=_h(ctx),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_convocatoria_campo_extra_retorna_422(ctx):
    """SPEC: extra='forbid' → unknown field 'tipo' → 422."""
    r = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "instancia": "Extra field",
            "dias": [{"fecha": "2026-09-10", "cupo_total": 5}],
            "tipo": "Parcial",
        },
        headers=_h(ctx),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crear_convocatoria_sin_permiso_retorna_403(ctx):
    """SPEC: ALUMNO without coloquios:gestionar → 403."""
    r = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_a_id"]),
            "cohorte_id": str(ctx["cohorte_a_id"]),
            "instancia": "No pass",
            "dias": [{"fecha": "2026-09-10", "cupo_total": 5}],
        },
        headers=_h(ctx, "alumno1"),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 6.2 — Importar candidatos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_importar_candidatos_registra_uno_por_alumno(ctx):
    """RED→GREEN: importar 2 alumnos → candidatos_agregados=2."""
    conv = await _crear_convocatoria(ctx)
    evaluacion_id = conv["id"]

    r = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidatos_agregados"] == 2


@pytest.mark.asyncio
async def test_importar_candidatos_reimportar_no_duplica(ctx):
    """TRIANGULATE: reimporting the same alumno doesn't duplicate (idempotent)."""
    conv = await _crear_convocatoria(ctx)
    evaluacion_id = conv["id"]

    alumno_ids = [str(ctx["auth_alumno1_id"])]

    # First import
    r1 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": alumno_ids},
        headers=_h(ctx),
    )
    assert r1.status_code == 200
    assert r1.json()["candidatos_agregados"] == 1

    # Re-import same alumno → added=0
    r2 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": alumno_ids},
        headers=_h(ctx),
    )
    assert r2.status_code == 200
    assert r2.json()["candidatos_agregados"] == 0


@pytest.mark.asyncio
async def test_importar_candidatos_convocatoria_otro_tenant_retorna_404(ctx):
    """SPEC: convocatoria belonging to tenant_b is invisible to tenant_a → 404."""
    # Create a convocatoria with tenant_b
    r_b = await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_b_id"]),
            "cohorte_id": str(ctx["cohorte_b_id"]),
            "instancia": "Eval B",
            "dias": [{"fecha": "2026-09-10", "cupo_total": 5}],
        },
        headers=_h(ctx, "coord_b"),
    )
    assert r_b.status_code == 201
    evaluacion_b_id = r_b.json()["id"]

    # Tenant A tries to import candidates into tenant_b convocatoria → 404
    r = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_b_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),  # tenant_a token
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 6.3 — Reservar con cupo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reservar_crea_reserva_activa(ctx):
    """RED→GREEN: alumno_candidato reserves → ReservaEvaluacion Activa."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-09-10", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    # Get the DiaEvaluacion id via agenda endpoint
    agenda_r = await ctx["client"].get(
        f"/api/coloquios/{evaluacion_id}/agenda",
        headers=_h(ctx),
    )
    assert agenda_r.status_code == 200
    # No reservas yet, but we need the dia id from the listar endpoint
    # Use listar to get dia info via creating another convocatoria — we'll query directly via service

    # Import alumno1 as candidate
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    # Get dia_evaluacion_id by listing convocatorias (the response doesn't include dias)
    # We need to add alumno and try to find the dia_id; let's get it via DB
    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    assert dia is not None
    dia_id = str(dia.id)

    # alumno1 reserves
    r = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "Activa"
    assert body["evaluacion_id"] == evaluacion_id
    assert body["dia_evaluacion_id"] == dia_id


@pytest.mark.asyncio
async def test_reservar_triangula_segundo_alumno_reduce_cupo(ctx):
    """TRIANGULATE: 2nd alumno also reserves → 2 active reservas in the day."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-09-20", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    # Import both alumnos
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion, ReservaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    # Both reserve
    r1 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r1.status_code == 201

    r2 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno2"),
    )
    assert r2.status_code == 201

    # Verify 2 active reservas in DB
    reservas = (await session.scalars(
        select(ReservaEvaluacion)
        .where(ReservaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(ReservaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
        .where(ReservaEvaluacion.estado == "Activa")
    )).all()
    assert len(reservas) == 2


@pytest.mark.asyncio
async def test_reservar_audit_log_registrado(ctx):
    """SPEC: audit log COLOQUIO_RESERVAR is created after successful reserva."""
    from sqlalchemy import select

    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-09-25", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )

    audit = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx["tenant_a_id"])
        .where(AuditLog.accion == "COLOQUIO_RESERVAR")
    )
    assert audit is not None


# ---------------------------------------------------------------------------
# 6.4 — Sin cupo rechaza
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sin_cupo_retorna_409(ctx):
    """RED→GREEN: cupo_total=1, 2 alumnos → 2nd gets 409 SinCupo."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-10-01", "cupo_total": 1}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    # First reserves successfully
    r1 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r1.status_code == 201

    # Second gets 409
    r2 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno2"),
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_sin_cupo_no_crea_reserva_extra(ctx):
    """TRIANGULATE: DB still has exactly 1 active reserva after the 409."""
    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion, ReservaEvaluacion

    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-10-05", "cupo_total": 1}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno2"),
    )

    reservas = (await session.scalars(
        select(ReservaEvaluacion)
        .where(ReservaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(ReservaEvaluacion.dia_evaluacion_id == dia.id)
        .where(ReservaEvaluacion.estado == "Activa")
    )).all()
    assert len(reservas) == 1


# ---------------------------------------------------------------------------
# 6.5 — Reglas de reserva
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserva_alumno_no_candidato_retorna_403(ctx):
    """SPEC: alumno not in candidates → 403 NoCandidato."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-10-10", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    # Don't import alumno1 as candidate

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    r = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),  # has evaluacion:reservar_instancia but not a candidate
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_reserva_duplicada_mismo_alumno_retorna_409(ctx):
    """SPEC: same alumno tries to reserve twice in same evaluacion → 409."""
    conv = await _crear_convocatoria(ctx, dias=[
        {"fecha": "2026-10-15", "cupo_total": 5},
        {"fecha": "2026-10-16", "cupo_total": 5},
    ])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dias = (await session.scalars(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
        .order_by(DiaEvaluacion.fecha.asc())
    )).all()

    # First reserve on day 1 → OK
    r1 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": str(dias[0].id)},
        headers=_h(ctx, "alumno1"),
    )
    assert r1.status_code == 201

    # Try to reserve again on day 2 → 409 ReservaDuplicada
    r2 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": str(dias[1].id)},
        headers=_h(ctx, "alumno1"),
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_reserva_convocatoria_cerrada_retorna_409(ctx):
    """SPEC: reserva in a Cerrada convocatoria → 409 ConvocatoriaCerrada."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-10-20", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    # Close the convocatoria
    r_close = await ctx["client"].patch(
        f"/api/coloquios/{evaluacion_id}",
        json={"estado": "Cerrada"},
        headers=_h(ctx),
    )
    assert r_close.status_code == 200

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    r = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# 6.6 — Cancelar libera cupo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancelar_reserva_estado_cancelada(ctx):
    """RED→GREEN: cancel an active reserva → estado=Cancelada."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-11-01", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    r_reserva = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r_reserva.status_code == 201
    reserva_id = r_reserva.json()["id"]

    r_cancel = await ctx["client"].patch(
        f"/api/coloquios/reservas/{reserva_id}",
        json={"estado": "Cancelada"},
        headers=_h(ctx, "alumno1"),
    )
    assert r_cancel.status_code == 200, r_cancel.text
    assert r_cancel.json()["estado"] == "Cancelada"


@pytest.mark.asyncio
async def test_cancelar_reserva_libera_cupo_permite_re_reservar(ctx):
    """TRIANGULATE: cancel then another alumno can reserve the freed slot."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-11-05", "cupo_total": 1}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    # alumno1 takes the only slot
    r1 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r1.status_code == 201
    reserva_id = r1.json()["id"]

    # alumno2 is blocked
    r_block = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno2"),
    )
    assert r_block.status_code == 409

    # alumno1 cancels
    r_cancel = await ctx["client"].patch(
        f"/api/coloquios/reservas/{reserva_id}",
        json={"estado": "Cancelada"},
        headers=_h(ctx, "alumno1"),
    )
    assert r_cancel.status_code == 200

    # alumno2 can now reserve
    r2 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno2"),
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_cancelar_reserva_ajena_retorna_404(ctx):
    """SPEC: canceling another alumno's reserva → 404 ReservaNoEncontrada."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-11-10", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    # alumno1 reserves
    r1 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )
    assert r1.status_code == 201
    reserva_id = r1.json()["id"]

    # alumno2 tries to cancel alumno1's reserva → 404
    # alumno2 needs the perm to even reach the endpoint
    # alumno2 has evaluacion:reservar_instancia so the router is accessible
    # but the service checks ownership → 404
    r_cancel = await ctx["client"].patch(
        f"/api/coloquios/reservas/{reserva_id}",
        json={"estado": "Cancelada"},
        headers=_h(ctx, "alumno2"),
    )
    assert r_cancel.status_code == 404


# ---------------------------------------------------------------------------
# 6.7 — Listado / métricas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_convocatorias_metricas_derivadas(ctx):
    """RED→GREEN: GET /api/coloquios returns convocados/reservas_activas/cupos_libres."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-12-01", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    # Import 2 candidates
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )

    # alumno1 reserves
    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dia = await session.scalar(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
    )
    dia_id = str(dia.id)

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": dia_id},
        headers=_h(ctx, "alumno1"),
    )

    r = await ctx["client"].get("/api/coloquios", headers=_h(ctx))
    assert r.status_code == 200, r.text
    convocatorias = r.json()
    assert len(convocatorias) >= 1

    ev = next(c for c in convocatorias if c["id"] == evaluacion_id)
    assert ev["convocados"] == 2
    assert ev["reservas_activas"] == 1
    assert ev["cupos_libres"] == 4  # 5 - 1


@pytest.mark.asyncio
async def test_listar_convocatorias_tenant_isolation(ctx):
    """SPEC: convocatoria from tenant_b does not appear in tenant_a listing."""
    # Create one in tenant_b
    await ctx["client"].post(
        "/api/coloquios",
        json={
            "materia_id": str(ctx["materia_b_id"]),
            "cohorte_id": str(ctx["cohorte_b_id"]),
            "instancia": "Eval B isolation",
            "dias": [{"fecha": "2026-12-05", "cupo_total": 5}],
        },
        headers=_h(ctx, "coord_b"),
    )

    # tenant_a sees nothing (no convocatorias in tenant_a yet)
    r = await ctx["client"].get("/api/coloquios", headers=_h(ctx))
    assert r.status_code == 200
    assert len(r.json()) == 0


@pytest.mark.asyncio
async def test_metricas_globales_agrega_tenant(ctx):
    """SPEC: GET /api/coloquios/metricas returns aggregated metrics."""
    # Create a convocatoria, import candidate, register result
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-12-10", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [str(ctx["auth_alumno1_id"])]},
        headers=_h(ctx),
    )

    # Register a result
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/resultados",
        json={"alumno_id": str(ctx["auth_alumno1_id"]), "nota_final": "8"},
        headers=_h(ctx),
    )

    r = await ctx["client"].get("/api/coloquios/metricas", headers=_h(ctx))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["convocados"] >= 1
    assert body["instancias_activas"] >= 1
    assert body["notas_registradas"] >= 1
    assert "reservas_activas" in body


# ---------------------------------------------------------------------------
# 6.8 — Resultados y agenda
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registrar_resultado_crea_entrada(ctx):
    """RED→GREEN: POST resultado creates ResultadoEvaluacion."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-12-15", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    r = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/resultados",
        json={"alumno_id": str(ctx["auth_alumno1_id"]), "nota_final": "Aprobado"},
        headers=_h(ctx),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nota_final"] == "Aprobado"
    assert body["evaluacion_id"] == evaluacion_id


@pytest.mark.asyncio
async def test_registrar_resultado_reregistrar_actualiza_sin_duplicar(ctx):
    """TRIANGULATE: re-registering same alumno updates nota_final, no duplicate."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-12-16", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/resultados",
        json={"alumno_id": str(ctx["auth_alumno1_id"]), "nota_final": "Aprobado"},
        headers=_h(ctx),
    )

    # Re-register with different nota
    r2 = await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/resultados",
        json={"alumno_id": str(ctx["auth_alumno1_id"]), "nota_final": "Desaprobado"},
        headers=_h(ctx),
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["nota_final"] == "Desaprobado"

    # GET resultados → only 1 entry
    r_list = await ctx["client"].get(
        f"/api/coloquios/{evaluacion_id}/resultados",
        headers=_h(ctx),
    )
    assert r_list.status_code == 200
    resultados = r_list.json()
    assert len(resultados) == 1
    assert resultados[0]["nota_final"] == "Desaprobado"


@pytest.mark.asyncio
async def test_listar_resultados_por_convocatoria(ctx):
    """SPEC: GET /api/coloquios/{id}/resultados lists all results for that eval."""
    conv = await _crear_convocatoria(ctx, dias=[{"fecha": "2026-12-17", "cupo_total": 5}])
    evaluacion_id = conv["id"]

    # Register 2 results
    for alumno_id, nota in [
        (ctx["auth_alumno1_id"], "8"),
        (ctx["auth_alumno2_id"], "6"),
    ]:
        await ctx["client"].post(
            f"/api/coloquios/{evaluacion_id}/resultados",
            json={"alumno_id": str(alumno_id), "nota_final": nota},
            headers=_h(ctx),
        )

    r = await ctx["client"].get(
        f"/api/coloquios/{evaluacion_id}/resultados",
        headers=_h(ctx),
    )
    assert r.status_code == 200
    resultados = r.json()
    assert len(resultados) == 2
    notas = {res["nota_final"] for res in resultados}
    assert notas == {"8", "6"}


@pytest.mark.asyncio
async def test_agenda_agrupa_reservas_por_dia(ctx):
    """SPEC: GET /api/coloquios/{id}/agenda groups active reservas by date."""
    conv = await _crear_convocatoria(ctx, dias=[
        {"fecha": "2026-12-20", "cupo_total": 5},
        {"fecha": "2026-12-21", "cupo_total": 5},
    ])
    evaluacion_id = conv["id"]

    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/candidatos",
        json={"alumno_ids": [
            str(ctx["auth_alumno1_id"]),
            str(ctx["auth_alumno2_id"]),
        ]},
        headers=_h(ctx),
    )

    from sqlalchemy import select
    from app.models.evaluaciones import DiaEvaluacion

    session = ctx["session"]
    dias = (await session.scalars(
        select(DiaEvaluacion)
        .where(DiaEvaluacion.tenant_id == ctx["tenant_a_id"])
        .where(DiaEvaluacion.evaluacion_id == uuid.UUID(evaluacion_id))
        .order_by(DiaEvaluacion.fecha.asc())
    )).all()

    # alumno1 → day 0, alumno2 → day 1
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": str(dias[0].id)},
        headers=_h(ctx, "alumno1"),
    )
    await ctx["client"].post(
        f"/api/coloquios/{evaluacion_id}/reservas",
        json={"dia_evaluacion_id": str(dias[1].id)},
        headers=_h(ctx, "alumno2"),
    )

    r = await ctx["client"].get(
        f"/api/coloquios/{evaluacion_id}/agenda",
        headers=_h(ctx),
    )
    assert r.status_code == 200, r.text
    agenda = r.json()

    # 2 days in agenda
    assert len(agenda) == 2

    # Day 0 has 1 reserva, day 1 has 1 reserva
    day_0 = next(d for d in agenda if d["fecha"] == "2026-12-20")
    day_1 = next(d for d in agenda if d["fecha"] == "2026-12-21")
    assert len(day_0["reservas"]) == 1
    assert len(day_1["reservas"]) == 1
