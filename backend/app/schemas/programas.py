from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


_TIPOS_FECHA = Literal["Parcial", "TP", "Coloquio", "Recuperatorio"]


class CrearProgramaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str = Field(min_length=1, max_length=255)
    referencia_archivo: str = Field(min_length=1)


class ProgramaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: str
    cargado_at: datetime
    created_at: datetime
    updated_at: datetime


class CrearFechaAcademicaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: _TIPOS_FECHA
    numero: int = Field(ge=1)
    periodo: str = Field(min_length=1, max_length=20)
    fecha: date
    titulo: str = Field(min_length=1, max_length=255)


class EditarFechaAcademicaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tipo: _TIPOS_FECHA | None = None
    numero: int | None = Field(default=None, ge=1)
    periodo: str | None = Field(default=None, min_length=1, max_length=20)
    fecha: date | None = None
    titulo: str | None = Field(default=None, min_length=1, max_length=255)


class FechaAcademicaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: str
    numero: int
    periodo: str
    fecha: date
    titulo: str
    created_at: datetime
    updated_at: datetime


class FragmentoLmsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str
