from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Carrera, Cohorte, Materia, Permiso, Rol, RolPermiso, Usuario
from app.models.audit import AuditLog
from app.models.usuarios import Asignacion
from app.core.database import get_session_factory
from tests.usuarios_test_utils import clean_database, ensure_schema


@pytest.fixture
async def equipos_app(valid_env):
    from app.api.v1.routers.equipos import router as equipos_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)
        from app.models import Tenant

        tenant_a = Tenant(name="Tenant A", slug="eq-a")
        tenant_b = Tenant(name="Tenant B", slug="eq-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        user_coord = AuthUser(tenant_id=tenant_a.id, email="coord@eq.local", password_hash=hash_password("P1!"), roles=["COORDINADOR"])
        user_plain = AuthUser(tenant_id=tenant_a.id, email="plain@eq.local", password_hash=hash_password("P1!"), roles=["ALUMNO"])
        user_b = AuthUser(tenant_id=tenant_b.id, email="b@eq.local", password_hash=hash_password("P1!"), roles=["COORDINADOR"])
        session.add_all([user_coord, user_plain, user_b])
        await session.flush()

        rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_b = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
        session.add_all([rol, rol_b])
        await session.flush()

        permiso = Permiso(tenant_id=tenant_a.id, nombre="equipos:asignar")
        permiso_b = Permiso(tenant_id=tenant_b.id, nombre="equipos:asignar")
        session.add_all([permiso, permiso_b])
        await session.flush()

        session.add_all([
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=permiso.id),
            RolPermiso(tenant_id=tenant_b.id, rol_id=rol_b.id, permiso_id=permiso_b.id),
        ])

        carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR", nombre="Carrera Test")
        session.add(carrera)
        await session.flush()
        cohorte = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia = Materia(tenant_id=tenant_a.id, codigo="MAT", nombre="Materia Test")
        session.add_all([cohorte, materia])
        await session.flush()

        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CAR-B", nombre="Carrera B")
        session.add(carrera_b)
        await session.flush()
        cohorte_b = Cohorte(tenant_id=tenant_b.id, carrera_id=carrera_b.id, nombre="2026-B", anio=2026, vig_desde=date(2026, 1, 1))
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
        session.add_all([cohorte_b, materia_b])
        await session.flush()

        usuario_coord = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=user_coord.id,
            nombre="Coord",
            apellidos="Docente",
            email_encrypted="enc-coord",
            email_hash="hash-coord",
        )
        usuario_extra = Usuario(
            tenant_id=tenant_a.id,
            nombre="Extra",
            apellidos="Profesor",
            email_encrypted="enc-extra",
            email_hash="hash-extra",
        )
        usuario_b = Usuario(
            tenant_id=tenant_b.id,
            auth_user_id=user_b.id,
            nombre="Docente",
            apellidos="B",
            email_encrypted="enc-b",
            email_hash="hash-b",
        )
        session.add_all([usuario_coord, usuario_extra, usuario_b])
        await session.commit()

        token_coord = create_access_token(user_id=str(user_coord.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"])
        token_plain = create_access_token(user_id=str(user_plain.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"])
        token_b = create_access_token(user_id=str(user_b.id), tenant_id=str(tenant_b.id), roles=["COORDINADOR"])

        app = FastAPI()
        app.include_router(equipos_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield (
                client,
                session,
                token_coord,
                token_plain,
                token_b,
                tenant_a.id,
                tenant_b.id,
                rol.id,
                carrera.id,
                cohorte.id,
                materia.id,
                usuario_coord.id,
                usuario_extra.id,
                usuario_b.id,
                user_coord.id,
            )


# ---------------------------------------------------------------------------
# 5.1 — mis-equipos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mis_equipos_returns_own_assignments(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, *_ = equipos_app

    asignacion = Asignacion(
        tenant_id=tenant_a_id,
        usuario_id=usuario_coord_id,
        rol_id=rol_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        desde=date.today() - timedelta(days=5),
        hasta=date.today() + timedelta(days=30),
    )
    session.add(asignacion)
    await session.commit()

    resp = await client.get("/api/equipos/mis-equipos", headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert str(data[0]["usuario_id"]) == str(usuario_coord_id)
    assert str(data[0]["materia_id"]) == str(materia_id)


@pytest.mark.asyncio
async def test_mis_equipos_empty_when_no_assignments(equipos_app):
    client, session, token_coord, *_ = equipos_app
    resp = await client.get("/api/equipos/mis-equipos", headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_mis_equipos_tenant_isolation(equipos_app):
    client, session, token_coord, _, token_b, tenant_a_id, tenant_b_id, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, _, usuario_b_id, _ = equipos_app

    asignacion_a = Asignacion(
        tenant_id=tenant_a_id,
        usuario_id=usuario_coord_id,
        rol_id=rol_id,
        desde=date.today(),
    )
    session.add(asignacion_a)
    await session.commit()

    resp_b = await client.get("/api/equipos/mis-equipos", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    # tenant_b user should see no assignments from tenant_a
    assert resp_b.json() == []


# ---------------------------------------------------------------------------
# 5.2 — list_asignaciones (filtros y guard)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_asignaciones_filter_by_materia(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, usuario_extra_id, *_ = equipos_app

    a1 = Asignacion(tenant_id=tenant_a_id, usuario_id=usuario_coord_id, rol_id=rol_id, materia_id=materia_id, desde=date.today())
    a2 = Asignacion(tenant_id=tenant_a_id, usuario_id=usuario_extra_id, rol_id=rol_id, desde=date.today())
    session.add_all([a1, a2])
    await session.commit()

    resp = await client.get(
        f"/api/equipos/asignaciones?materia_id={materia_id}",
        headers={"Authorization": f"Bearer {token_coord}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert str(data[0]["materia_id"]) == str(materia_id)


@pytest.mark.asyncio
async def test_list_asignaciones_requires_permission(equipos_app):
    client, _, _, token_plain, *_ = equipos_app
    resp = await client.get("/api/equipos/asignaciones", headers={"Authorization": f"Bearer {token_plain}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 5.3 — buscar_docentes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_buscar_docentes_case_insensitive(equipos_app):
    client, _, token_coord, *_ = equipos_app

    resp = await client.get("/api/equipos/docentes/buscar?q=coo", headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    nombres = [d["nombre"].lower() + " " + d["apellidos"].lower() for d in data]
    assert any("coord" in n or "docente" in n for n in nombres)


@pytest.mark.asyncio
async def test_buscar_docentes_no_match(equipos_app):
    client, _, token_coord, *_ = equipos_app
    resp = await client.get("/api/equipos/docentes/buscar?q=zzznomatch", headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 5.4 — asignacion_masiva
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_asignacion_masiva_creates_assignments(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, usuario_extra_id, *_ = equipos_app

    payload = {
        "usuario_ids": [str(usuario_coord_id), str(usuario_extra_id)],
        "rol_id": str(rol_id),
        "materia_id": str(materia_id),
        "carrera_id": str(carrera_id),
        "cohorte_id": str(cohorte_id),
        "desde": str(date.today()),
    }
    resp = await client.post("/api/equipos/asignaciones/masiva", json=payload, headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 201
    assert resp.json()["asignaciones_creadas"] == 2

    from sqlalchemy import select
    from app.models.audit import AuditLog
    audit_rows = list((await session.scalars(select(AuditLog).where(AuditLog.accion == "ASIGNACION_MODIFICAR"))).all())
    assert len(audit_rows) >= 1
    assert audit_rows[-1].filas_afectadas == 2


@pytest.mark.asyncio
async def test_asignacion_masiva_409_on_duplicate(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, *_ = equipos_app

    existing = Asignacion(
        tenant_id=tenant_a_id,
        usuario_id=usuario_coord_id,
        rol_id=rol_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        desde=date.today() - timedelta(days=1),
        hasta=date.today() + timedelta(days=30),
    )
    session.add(existing)
    await session.commit()

    payload = {
        "usuario_ids": [str(usuario_coord_id)],
        "rol_id": str(rol_id),
        "materia_id": str(materia_id),
        "carrera_id": str(carrera_id),
        "cohorte_id": str(cohorte_id),
        "desde": str(date.today()),
    }
    resp = await client.post("/api/equipos/asignaciones/masiva", json=payload, headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 5.5 — clonar_equipo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clonar_equipo_clones_assignments(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, usuario_extra_id, *_ = equipos_app

    vigente = Asignacion(
        tenant_id=tenant_a_id,
        usuario_id=usuario_coord_id,
        rol_id=rol_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        desde=date.today() - timedelta(days=5),
        hasta=date.today() + timedelta(days=30),
    )
    session.add(vigente)
    await session.flush()

    nueva_cohorte = Cohorte(tenant_id=tenant_a_id, carrera_id=carrera_id, nombre="2027", anio=2027, vig_desde=date(2027, 1, 1))
    session.add(nueva_cohorte)
    await session.commit()

    payload = {
        "origen": {"materia_id": str(materia_id), "carrera_id": str(carrera_id), "cohorte_id": str(cohorte_id)},
        "destino": {"materia_id": str(materia_id), "carrera_id": str(carrera_id), "cohorte_id": str(nueva_cohorte.id), "desde": str(date(2027, 3, 1))},
    }
    resp = await client.post("/api/equipos/clonar", json=payload, headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 201
    assert resp.json()["asignaciones_clonadas"] == 1

    from sqlalchemy import select
    audit_rows = list((await session.scalars(select(AuditLog).where(AuditLog.accion == "ASIGNACION_MODIFICAR"))).all())
    assert any(r.filas_afectadas == 1 for r in audit_rows)


@pytest.mark.asyncio
async def test_clonar_equipo_422_without_vigentes(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, *_ = equipos_app

    nueva_cohorte = Cohorte(tenant_id=tenant_a_id, carrera_id=carrera_id, nombre="2028", anio=2028, vig_desde=date(2028, 1, 1))
    session.add(nueva_cohorte)
    await session.commit()

    payload = {
        "origen": {"materia_id": str(materia_id), "carrera_id": str(carrera_id), "cohorte_id": str(cohorte_id)},
        "destino": {"materia_id": str(materia_id), "carrera_id": str(carrera_id), "cohorte_id": str(nueva_cohorte.id), "desde": str(date(2028, 3, 1))},
    }
    resp = await client.post("/api/equipos/clonar", json=payload, headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5.6 — modificar_vigencia_equipo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modificar_vigencia_equipo_updates_all(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, usuario_extra_id, *_ = equipos_app

    a1 = Asignacion(tenant_id=tenant_a_id, usuario_id=usuario_coord_id, rol_id=rol_id, materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id, desde=date.today())
    a2 = Asignacion(tenant_id=tenant_a_id, usuario_id=usuario_extra_id, rol_id=rol_id, materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id, desde=date.today())
    session.add_all([a1, a2])
    await session.commit()

    nueva_hasta = date.today() + timedelta(days=90)
    payload = {
        "materia_id": str(materia_id),
        "carrera_id": str(carrera_id),
        "cohorte_id": str(cohorte_id),
        "desde": str(date.today()),
        "hasta": str(nueva_hasta),
    }
    resp = await client.patch("/api/equipos/vigencia", json=payload, headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 200
    assert resp.json()["asignaciones_actualizadas"] == 2

    from sqlalchemy import select
    audit_rows = list((await session.scalars(select(AuditLog).where(AuditLog.accion == "ASIGNACION_MODIFICAR"))).all())
    assert any(r.filas_afectadas == 2 for r in audit_rows)


@pytest.mark.asyncio
async def test_modificar_vigencia_equipo_404_when_not_found(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, _, carrera_id, cohorte_id, materia_id, *_ = equipos_app

    payload = {
        "materia_id": str(materia_id),
        "carrera_id": str(carrera_id),
        "cohorte_id": str(cohorte_id),
        "desde": str(date.today()),
    }
    resp = await client.patch("/api/equipos/vigencia", json=payload, headers={"Authorization": f"Bearer {token_coord}"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5.7 — exportar_equipo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exportar_equipo_returns_csv_with_content_disposition(equipos_app):
    client, session, token_coord, _, _, tenant_a_id, _, rol_id, carrera_id, cohorte_id, materia_id, usuario_coord_id, *_ = equipos_app

    a = Asignacion(tenant_id=tenant_a_id, usuario_id=usuario_coord_id, rol_id=rol_id, materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id, desde=date.today())
    session.add(a)
    await session.commit()

    resp = await client.get(
        f"/api/equipos/exportar?materia_id={materia_id}&carrera_id={carrera_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_coord}"},
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "usuario_id" in resp.text


@pytest.mark.asyncio
async def test_exportar_equipo_empty_returns_headers_only(equipos_app):
    client, _, token_coord, _, _, _, _, _, carrera_id, cohorte_id, materia_id, *_ = equipos_app

    resp = await client.get(
        f"/api/equipos/exportar?materia_id={materia_id}&carrera_id={carrera_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_coord}"},
    )
    assert resp.status_code == 200
    lines = [l for l in resp.text.strip().splitlines() if l]
    assert len(lines) == 1
    assert "usuario_id" in lines[0]
