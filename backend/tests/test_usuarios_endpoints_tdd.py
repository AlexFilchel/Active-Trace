from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Carrera, Cohorte, Materia, Permiso, Rol, RolPermiso, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema
from app.core.database import get_session_factory


@pytest.fixture
async def usuarios_app(valid_env):
    from app.api.v1.routers.usuarios import asignaciones_router, usuarios_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)
        from app.models import Tenant

        tenant_a = Tenant(name="Tenant A", slug="usuarios-a")
        tenant_b = Tenant(name="Tenant B", slug="usuarios-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        user_admin = AuthUser(tenant_id=tenant_a.id, email="admin@test.local", password_hash=hash_password("Pass1!"), roles=["ADMIN"])
        user_coord = AuthUser(tenant_id=tenant_a.id, email="coord@test.local", password_hash=hash_password("Pass1!"), roles=["COORDINADOR"])
        user_plain = AuthUser(tenant_id=tenant_a.id, email="plain@test.local", password_hash=hash_password("Pass1!"), roles=["ALUMNO"])
        session.add_all([user_admin, user_coord, user_plain])
        await session.flush()

        rol_admin = Rol(tenant_id=tenant_a.id, nombre="ADMIN")
        rol_coord = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        rol_alumno = Rol(tenant_id=tenant_a.id, nombre="ALUMNO")
        session.add_all([rol_admin, rol_coord, rol_alumno])
        await session.flush()

        permiso_usuarios = Permiso(tenant_id=tenant_a.id, nombre="usuarios:gestionar")
        permiso_equipos = Permiso(tenant_id=tenant_a.id, nombre="equipos:asignar")
        session.add_all([permiso_usuarios, permiso_equipos])
        await session.flush()

        session.add_all(
            [
                RolPermiso(tenant_id=tenant_a.id, rol_id=rol_admin.id, permiso_id=permiso_usuarios.id),
                RolPermiso(tenant_id=tenant_a.id, rol_id=rol_admin.id, permiso_id=permiso_equipos.id),
                RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coord.id, permiso_id=permiso_equipos.id),
            ]
        )

        carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR", nombre="Carrera")
        session.add(carrera)
        await session.flush()
        cohorte = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia = Materia(tenant_id=tenant_a.id, codigo="MAT", nombre="Materia")
        session.add_all([cohorte, materia])
        await session.flush()

        carrera_b = Carrera(tenant_id=tenant_b.id, codigo="CAR-B", nombre="Carrera B")
        session.add(carrera_b)
        await session.flush()
        cohorte_b = Cohorte(tenant_id=tenant_b.id, carrera_id=carrera_b.id, nombre="2027", anio=2027, vig_desde=date(2027, 1, 1))
        materia_b = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
        session.add_all([cohorte_b, materia_b])
        await session.flush()

        usuario_dominio = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=user_coord.id,
            nombre="Coord",
            apellidos="User",
            email_encrypted="enc-coord",
            email_hash="hash-coord",
        )
        usuario_admin = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=user_admin.id,
            nombre="Admin",
            apellidos="User",
            email_encrypted="enc-admin",
            email_hash="hash-admin",
        )
        usuario_otro_tenant = Usuario(
            tenant_id=tenant_b.id,
            nombre="Otra",
            apellidos="Persona",
            email_encrypted="enc-other",
            email_hash="hash-other",
        )
        session.add_all([usuario_dominio, usuario_admin, usuario_otro_tenant])
        await session.commit()

        token_admin = create_access_token(user_id=str(user_admin.id), tenant_id=str(tenant_a.id), roles=["ADMIN"])
        token_coord = create_access_token(user_id=str(user_coord.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"])
        token_plain = create_access_token(user_id=str(user_plain.id), tenant_id=str(tenant_a.id), roles=["ALUMNO"])
        token_other_tenant = create_access_token(user_id=str(user_admin.id), tenant_id=str(tenant_b.id), roles=["ADMIN"])

        app = FastAPI()
        app.include_router(usuarios_router)
        app.include_router(asignaciones_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield (
                client,
                token_admin,
                token_coord,
                token_plain,
                token_other_tenant,
                carrera.id,
                cohorte.id,
                materia.id,
                usuario_dominio.id,
                usuario_admin.id,
                carrera_b.id,
                cohorte_b.id,
                materia_b.id,
                usuario_otro_tenant.id,
            )


@pytest.mark.asyncio
async def test_usuarios_endpoints_guard_and_filter_sensitive_fields(usuarios_app):
    client, token_admin, _, token_plain, _, *_ = usuarios_app

    unauthorized = await client.get("/api/admin/usuarios")
    assert unauthorized.status_code == 401

    forbidden = await client.get("/api/admin/usuarios", headers={"Authorization": f"Bearer {token_plain}"})
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/admin/usuarios",
        json={"nombre": "Ada", "apellidos": "Lovelace", "email": "ada@test.local", "dni": "12345678"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["email"] == "ada@test.local"
    assert "email_encrypted" not in payload
    assert "email_hash" not in payload

    invalid = await client.post(
        "/api/admin/usuarios",
        json={
            "nombre": "Ada",
            "apellidos": "Lovelace",
            "email": "ada-private@test.local",
            "tenant_id": "forbidden",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert invalid.status_code == 422
    assert "ada-private@test.local" not in invalid.text


@pytest.mark.asyncio
async def test_request_business_identifiers_do_not_override_session_identity(usuarios_app):
    client, _, _, token_plain, _, _, _, _, usuario_coord_id, usuario_admin_id, *_ = usuarios_app

    forbidden_usuario = await client.post(
        "/api/admin/usuarios",
        json={
            "nombre": "Intruso",
            "apellidos": "Sin Permiso",
            "email": "intruso@test.local",
            "legajo": "ADMIN-001",
            "auth_user_id": str(usuario_admin_id),
        },
        headers={"Authorization": f"Bearer {token_plain}"},
    )
    assert forbidden_usuario.status_code == 403

    forbidden_asignacion = await client.post(
        "/api/asignaciones",
        json={
            "usuario_id": str(usuario_coord_id),
            "rol_id": str(await _get_role_id("COORDINADOR")),
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token_plain}"},
    )
    assert forbidden_asignacion.status_code == 403


@pytest.mark.asyncio
async def test_asignaciones_endpoints_guard_tenant_isolation_and_vigencia_state(usuarios_app):
    client, token_admin, token_coord, _, token_other_tenant, carrera_id, cohorte_id, materia_id, usuario_coord_id, usuario_admin_id, *_ = usuarios_app

    forbidden = await client.get("/api/asignaciones", headers={"Authorization": f"Bearer {token_other_tenant}"})
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/asignaciones",
        json={
            "usuario_id": str(usuario_coord_id),
            "rol_id": str(await _get_role_id("COORDINADOR")),
            "carrera_id": str(carrera_id),
            "cohorte_id": str(cohorte_id),
            "materia_id": str(materia_id),
            "responsable_id": str(usuario_admin_id),
            "desde": str(date.today() - timedelta(days=1)),
            "hasta": str(date.today() + timedelta(days=1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert created.status_code == 201
    assert created.json()["estado_vigencia"] == "Vigente"

    expired = await client.post(
        "/api/asignaciones",
        json={
            "usuario_id": str(usuario_coord_id),
            "rol_id": str(await _get_role_id("COORDINADOR")),
            "desde": str(date.today() - timedelta(days=10)),
            "hasta": str(date.today() - timedelta(days=1)),
        },
        headers={"Authorization": f"Bearer {token_coord}"},
    )
    assert expired.status_code == 201
    assert expired.json()["estado_vigencia"] == "Vencida"

    filtered = await client.get(
        f"/api/asignaciones?usuario_id={usuario_coord_id}&materia_id={materia_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1


@pytest.mark.asyncio
async def test_asignaciones_endpoints_reject_foreign_tenant_context_and_responsable(usuarios_app):
    (
        client,
        token_admin,
        _,
        _,
        _,
        _carrera_id,
        _cohorte_id,
        _materia_id,
        usuario_coord_id,
        _usuario_admin_id,
        _foreign_carrera_id,
        foreign_cohorte_id,
        foreign_materia_id,
        foreign_usuario_id,
    ) = usuarios_app

    base_payload = {
        "usuario_id": str(usuario_coord_id),
        "rol_id": str(await _get_role_id("COORDINADOR")),
        "desde": str(date.today()),
    }

    for extra_field, extra_value in {
        "materia_id": foreign_materia_id,
        "cohorte_id": foreign_cohorte_id,
        "responsable_id": foreign_usuario_id,
    }.items():
        response = await client.post(
            "/api/asignaciones",
            json={**base_payload, extra_field: str(extra_value)},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_asignaciones_endpoints_support_get_patch_delete_and_hide_soft_deleted_by_default(usuarios_app):
    client, token_admin, _, _, _, carrera_id, cohorte_id, materia_id, usuario_coord_id, usuario_admin_id, *_ = usuarios_app

    created = await client.post(
        "/api/asignaciones",
        json={
            "usuario_id": str(usuario_coord_id),
            "rol_id": str(await _get_role_id("COORDINADOR")),
            "carrera_id": str(carrera_id),
            "cohorte_id": str(cohorte_id),
            "materia_id": str(materia_id),
            "responsable_id": str(usuario_admin_id),
            "comisiones": ["A"],
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert created.status_code == 201
    asignacion_id = created.json()["id"]

    fetched = await client.get(f"/api/asignaciones/{asignacion_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert fetched.status_code == 200
    assert fetched.json()["comisiones"] == ["A"]

    updated = await client.patch(
        f"/api/asignaciones/{asignacion_id}",
        json={"comisiones": ["A", "B"]},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert updated.status_code == 200
    assert updated.json()["comisiones"] == ["A", "B"]

    deleted = await client.delete(f"/api/asignaciones/{asignacion_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert deleted.status_code == 204

    listed = await client.get(
        f"/api/asignaciones?usuario_id={usuario_coord_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert listed.status_code == 200
    assert all(item["id"] != asignacion_id for item in listed.json())

    missing = await client.get(f"/api/asignaciones/{asignacion_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert missing.status_code == 404


async def _get_role_id(nombre: str):
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(__import__("sqlalchemy").text("SELECT id FROM rol WHERE nombre = :nombre ORDER BY created_at ASC LIMIT 1"), {"nombre": nombre})
        return result.scalar_one()
