"""Schemas Pydantic v2 para estructura académica.

extra='forbid' en todos — tenant_id nunca en el request body.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EstadoCarrera = Literal["Activa", "Inactiva"]
EstadoCohorte = Literal["Activa", "Inactiva"]
EstadoMateria = Literal["Activa", "Inactiva"]


# ---------------------------------------------------------------------------
# Carrera
# ---------------------------------------------------------------------------

class CarreraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(max_length=50)
    nombre: str = Field(max_length=200)


class CarreraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, max_length=200)
    estado: EstadoCarrera | None = None


class CarreraResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Cohorte
# ---------------------------------------------------------------------------

class CohorteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carrera_id: uuid.UUID
    nombre: str = Field(max_length=100)
    anio: int
    vig_desde: date
    vig_hasta: date | None = None


class CohorteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, max_length=100)
    anio: int | None = None
    vig_desde: date | None = None
    vig_hasta: date | None = None
    estado: EstadoCohorte | None = None


class CohorteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: date | None
    estado: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Materia
# ---------------------------------------------------------------------------

class MateriaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(max_length=50)
    nombre: str = Field(max_length=200)


class MateriaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, max_length=200)
    estado: EstadoMateria | None = None


class MateriaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: str
    created_at: datetime
    updated_at: datetime
