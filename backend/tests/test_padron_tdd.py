from __future__ import annotations

import io
import uuid
from datetime import date

import openpyxl
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.core.database import get_session_factory
from app.core.security import create_access_token, hash_password
from app.models import AuthUser, Carrera, Cohorte, Materia, Permiso, Rol, RolPermiso, Tenant
from app.models.base import Tenant as TenantModel
from app.models.padron import EntradaPadron, VersionPadron
from app.models.usuarios import Usuario
from app.services.padron_parser import ParseError, parse_file
from tests.usuarios_test_utils import clean_database, ensure_schema


# ---------------------------------------------------------------------------
# Helper — build xlsx file bytes
# ---------------------------------------------------------------------------

def make_xlsx(rows: list[dict], headers: list[str] | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    if headers is None:
        headers = ["Nombre", "Apellido(s)", "Dirección de correo", "Grupos"]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_csv(rows: list[dict], headers: list[str] | None = None) -> bytes:
    if headers is None:
        headers = ["Nombre", "Apellido(s)", "Dirección de correo", "Grupos"]
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(row.get(h, "") for h in headers))
    return "\n".join(lines).encode("utf-8")


SAMPLE_ROWS = [
    {"Nombre": "Ana", "Apellido(s)": "Lopez", "Dirección de correo": "ana@test.com", "Grupos": "A"},
    {"Nombre": "Juan", "Apellido(s)": "Perez", "Dirección de correo": "juan@test.com", "Grupos": "B"},
]


# ---------------------------------------------------------------------------
# 8.1 — Parser unit tests (no DB)
# ---------------------------------------------------------------------------

class TestParser:
    def test_xlsx_columns_loaded(self):
        content = make_xlsx(SAMPLE_ROWS)
        rows = parse_file(content, "padron.xlsx")
        assert len(rows) == 2
        assert rows[0]["nombre"] == "Ana"
        assert rows[0]["email"] == "ana@test.com"
        assert rows[0]["comision"] == "A"

    def test_csv_columns_loaded(self):
        content = make_csv(SAMPLE_ROWS)
        rows = parse_file(content, "padron.csv")
        assert len(rows) == 2
        assert rows[1]["apellidos"] == "Perez"

    def test_missing_column_raises_parse_error(self):
        # CSV without email column
        content = b"Nombre,Apellido(s)\nAna,Lopez"
        with pytest.raises(ParseError) as exc_info:
            parse_file(content, "padron.csv")
        assert "email" in exc_info.value.missing_columns

    def test_empty_file_raises_parse_error(self):
        content = make_xlsx([], headers=["Nombre", "Apellido(s)", "Dirección de correo", "Grupos"])
        with pytest.raises(ParseError) as exc_info:
            parse_file(content, "padron.xlsx")
        assert "no contiene alumnos" in exc_info.value.detail.lower()

    def test_case_insensitive_headers(self):
        content = b"nombre,apellidos,email\nAna,Lopez,ana@test.com"
        rows = parse_file(content, "padron.csv")
        assert rows[0]["nombre"] == "Ana"
        assert rows[0]["email"] == "ana@test.com"


# ---------------------------------------------------------------------------
# Fixture — padron_app with DB
# ---------------------------------------------------------------------------

@pytest.fixture
async def padron_app(valid_env):
    from app.api.v1.routers.padron import router as padron_router

    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Padron A", slug="pad-a")
        tenant_b = Tenant(name="Padron B", slug="pad-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        user_a = AuthUser(tenant_id=tenant_a.id, email="coord@pad.local", password_hash=hash_password("P1!"), roles=["COORDINADOR"])
        user_b = AuthUser(tenant_id=tenant_b.id, email="coord@pad-b.local", password_hash=hash_password("P1!"), roles=["COORDINADOR"])
        session.add_all([user_a, user_b])
        await session.flush()

        rol_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        permiso_a = Permiso(tenant_id=tenant_a.id, nombre="padron:gestionar")
        session.add_all([rol_a, permiso_a])
        await session.flush()
        session.add(RolPermiso(tenant_id=tenant_a.id, rol_id=rol_a.id, permiso_id=permiso_a.id))

        carrera_a = Carrera(tenant_id=tenant_a.id, codigo="CAR-P", nombre="Carrera Padron")
        session.add(carrera_a)
        await session.flush()
        cohorte_a = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera_a.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
        materia_a = Materia(tenant_id=tenant_a.id, codigo="MAT-P", nombre="Materia Padron")
        session.add_all([cohorte_a, materia_a])
        await session.flush()

        usuario_a = Usuario(
            tenant_id=tenant_a.id,
            auth_user_id=user_a.id,
            nombre="Coord",
            apellidos="Padron",
            email_encrypted="enc-coord-p",
            email_hash="hash-coord-p",
        )
        session.add(usuario_a)
        await session.commit()

        token_a = create_access_token(user_id=str(user_a.id), tenant_id=str(tenant_a.id), roles=["COORDINADOR"])
        token_b = create_access_token(user_id=str(user_b.id), tenant_id=str(tenant_b.id), roles=["COORDINADOR"])

        app = FastAPI()
        app.include_router(padron_router)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield (
                client,
                session,
                token_a,
                token_b,
                tenant_a.id,
                tenant_b.id,
                materia_a.id,
                cohorte_a.id,
                usuario_a.id,
            )


# ---------------------------------------------------------------------------
# 8.2 — Service: cargar_desde_archivo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cargar_crea_version_y_entradas(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, usuario_a_id = padron_app

    content = make_xlsx(SAMPLE_ROWS)
    resp = await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["entradas_cargadas"] == 2
    assert data["version_anterior_desactivada"] is False
    assert data["version_id"]


@pytest.mark.asyncio
async def test_segunda_carga_desactiva_version_anterior(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    content = make_xlsx(SAMPLE_ROWS)
    await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp = await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron2.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    assert resp.json()["version_anterior_desactivada"] is True


@pytest.mark.asyncio
async def test_cargar_columna_faltante_retorna_422(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    content = b"Nombre,Apellido(s)\nAna,Lopez"
    resp = await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron.csv", content, "text/csv")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 8.3 — GET /api/padron/activo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_padron_activo_devuelve_entradas(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    content = make_xlsx(SAMPLE_ROWS)
    await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp = await client.get(
        f"/api/padron/activo?materia_id={materia_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] is not None
    assert len(data["entradas"]) == 2
    emails = {e["email"] for e in data["entradas"]}
    assert "ana@test.com" in emails


@pytest.mark.asyncio
async def test_get_padron_sin_version_activa_retorna_vacio(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    resp = await client.get(
        f"/api/padron/activo?materia_id={materia_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] is None
    assert data["entradas"] == []


@pytest.mark.asyncio
async def test_get_padron_sin_permiso_retorna_403(padron_app):
    client, session, token_a, token_b, _, _, materia_id, cohorte_id, _ = padron_app

    # token_b belongs to tenant_b which has no padron:gestionar permission set up
    resp = await client.get(
        f"/api/padron/activo?materia_id={materia_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 8.4 — POST /api/padron/cargar: permission guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cargar_sin_permiso_retorna_403(padron_app):
    client, session, _, token_b, _, _, materia_id, cohorte_id, _ = padron_app

    content = make_csv(SAMPLE_ROWS)
    resp = await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron.csv", content, "text/csv")},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 8.5 — DELETE /api/padron/activo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_descartar_padron_exitoso(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    content = make_xlsx(SAMPLE_ROWS)
    await client.post(
        f"/api/padron/cargar?materia_id={materia_id}&cohorte_id={cohorte_id}",
        files={"file": ("padron.xlsx", content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp = await client.delete(
        f"/api/padron/activo?materia_id={materia_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    assert resp.json()["entradas_descartadas"] == 2


@pytest.mark.asyncio
async def test_descartar_sin_version_activa_retorna_404(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    resp = await client.delete(
        f"/api/padron/activo?materia_id={materia_id}&cohorte_id={cohorte_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8.6 — Moodle WS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cargar_moodle_tenant_sin_config_retorna_422(padron_app):
    client, session, token_a, _, _, _, materia_id, cohorte_id, _ = padron_app

    resp = await client.post(
        "/api/padron/cargar-moodle",
        json={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id), "moodle_course_id": 1},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 422
    assert "Moodle Web Services" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cargar_moodle_ws_error_retorna_502(padron_app):
    from app.integrations.moodle_ws import MoodleWSError

    client, session, token_a, _, tenant_a_id, _, materia_id, cohorte_id, _ = padron_app

    # Configure WS on tenant
    tenant = await session.get(TenantModel, tenant_a_id)
    from app.core.security import encrypt_value
    tenant.moodle_ws_url = "http://fake-moodle.test"
    tenant.moodle_ws_token_encrypted = encrypt_value("fake-token")
    await session.commit()

    with patch("app.services.padron_service.MoodleWSClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.get_enrolled_users.side_effect = MoodleWSError("Moodle connection error", status_code=502)

        resp = await client.post(
            "/api/padron/cargar-moodle",
            json={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id), "moodle_course_id": 42},
            headers={"Authorization": f"Bearer {token_a}"},
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_cargar_moodle_exitoso(padron_app):
    client, session, token_a, _, tenant_a_id, _, materia_id, cohorte_id, _ = padron_app

    tenant = await session.get(TenantModel, tenant_a_id)
    from app.core.security import encrypt_value
    tenant.moodle_ws_url = "http://fake-moodle.test"
    tenant.moodle_ws_token_encrypted = encrypt_value("fake-token")
    await session.commit()

    moodle_users = [
        {"firstname": "Ana", "lastname": "Lopez", "email": "ana@moodle.test"},
        {"firstname": "Juan", "lastname": "Perez", "email": "juan@moodle.test"},
    ]

    with patch("app.services.padron_service.MoodleWSClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.get_enrolled_users.return_value = moodle_users

        resp = await client.post(
            "/api/padron/cargar-moodle",
            json={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id), "moodle_course_id": 10},
            headers={"Authorization": f"Bearer {token_a}"},
        )
    assert resp.status_code == 201
    assert resp.json()["entradas_cargadas"] == 2
