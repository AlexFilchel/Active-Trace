from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.usuarios import AsignacionCreate, UsuarioCreate, UsuarioUpdate


def test_usuario_schemas_forbid_internal_fields_and_tenant_id():
    with pytest.raises(ValidationError):
        UsuarioCreate(nombre="Ada", apellidos="Lovelace", email="ada@test.local", tenant_id="x")

    with pytest.raises(ValidationError):
        UsuarioCreate(nombre="Ada", apellidos="Lovelace", email="ada@test.local", email_hash="x")

    with pytest.raises(ValidationError):
        UsuarioUpdate(email_encrypted="secret")


def test_asignacion_schema_rejects_invalid_dates():
    with pytest.raises(ValidationError):
        AsignacionCreate(
            usuario_id="00000000-0000-0000-0000-000000000001",
            rol_id="00000000-0000-0000-0000-000000000002",
            desde=date(2026, 5, 10),
            hasta=date(2026, 5, 1),
        )
