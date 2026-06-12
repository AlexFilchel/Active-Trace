from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actividades_numericas: list[str]
    actividades_textuales: list[str]


class ImportarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    actividades_seleccionadas: list[str] = Field(default_factory=list)


class ImportarResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calificaciones_importadas: int


class VaciadoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eliminadas: int


class SinCalificarItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    actividad: str


class ReporteFinalizacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sin_calificar: list[SinCalificarItem]


class UmbralRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    umbral_pct: Decimal = Field(ge=0, le=100)
    valores_aprobatorios: list[str] = Field(min_length=1)


class UmbralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    umbral_pct: Decimal
    valores_aprobatorios: list[str]
    es_defecto: bool
