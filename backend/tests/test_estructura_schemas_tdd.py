"""TDD tests for schemas de estructura académica.

Covers:
- extra='forbid': tenant_id en body lanza ValidationError
- extra='forbid': campo desconocido lanza ValidationError
- Validación de estado con Literal
- CarreraUpdate con campos opcionales
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.estructura import (
    CarreraCreate,
    CarreraUpdate,
    CohorteCreate,
    MateriaCreate,
    MateriaUpdate,
)


def test_carrera_create_tenant_id_en_body_lanza_validation_error():
    """CarreraCreate con tenant_id en el body lanza ValidationError (extra=forbid)."""
    with pytest.raises(ValidationError):
        CarreraCreate(codigo="X", nombre="Y", tenant_id=str(uuid.uuid4()))


def test_carrera_create_campo_desconocido_lanza_validation_error():
    """CarreraCreate con campo desconocido lanza ValidationError."""
    with pytest.raises(ValidationError):
        CarreraCreate(codigo="X", nombre="Y", campo_extra="no-permitido")


def test_carrera_create_valida_datos_correctos():
    """CarreraCreate acepta datos válidos."""
    c = CarreraCreate(codigo="TUPAD", nombre="Tecnicatura UP A Distancia")
    assert c.codigo == "TUPAD"
    assert c.nombre == "Tecnicatura UP A Distancia"


def test_carrera_update_todos_campos_son_opcionales():
    """CarreraUpdate puede instanciarse sin campos — son todos opcionales."""
    u = CarreraUpdate()
    assert u.nombre is None
    assert u.estado is None


def test_carrera_update_estado_invalido_lanza_error():
    """CarreraUpdate con estado fuera del Literal lanza ValidationError."""
    with pytest.raises(ValidationError):
        CarreraUpdate(estado="Pendiente")


def test_cohorte_create_campo_desconocido_lanza_validation_error():
    """CohorteCreate con campo extra lanza ValidationError."""
    with pytest.raises(ValidationError):
        CohorteCreate(
            carrera_id=uuid.uuid4(),
            nombre="MAR-2026",
            anio=2026,
            vig_desde=date(2026, 3, 1),
            campo_extra="x",
        )


def test_cohorte_create_vig_hasta_es_opcional():
    """CohorteCreate acepta vig_hasta=None (vigencia abierta)."""
    c = CohorteCreate(
        carrera_id=uuid.uuid4(),
        nombre="AGO-2025",
        anio=2025,
        vig_desde=date(2025, 8, 1),
    )
    assert c.vig_hasta is None


def test_materia_create_tenant_id_en_body_lanza_validation_error():
    """MateriaCreate con tenant_id en el body lanza ValidationError."""
    with pytest.raises(ValidationError):
        MateriaCreate(codigo="PROG_I", nombre="Programación I", tenant_id=str(uuid.uuid4()))


def test_materia_update_estado_invalido_lanza_error():
    """MateriaUpdate con estado fuera del Literal lanza ValidationError."""
    with pytest.raises(ValidationError):
        MateriaUpdate(estado="Borrada")
