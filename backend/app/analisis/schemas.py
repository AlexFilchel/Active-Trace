from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseAnalisisQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comision: str | None = None
    regional: str | None = None
    search: str | None = None


class RankingQuery(BaseAnalisisQuery):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class MonitorQuery(BaseAnalisisQuery):
    estado: Literal["todos", "atrasado", "al_dia"] = "todos"
    criterio: Literal["riesgo_desc", "aprobadas_desc", "nombre_asc"] = "riesgo_desc"
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class PaginationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int
    page_size: int
    total_items: int


class AtrasadoMotivoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["actividad_faltante", "nota_bajo_umbral"]
    actividad: str
    valor_observado: str | None = None
    umbral_aplicable: Decimal | None = None


class AtrasadoItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    comision: str | None = None
    regional: str | None = None
    motivos: list[AtrasadoMotivoResponse]
    actividades_pendientes: int
    aprobadas_count: int


class AtrasadosResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_items: int
    items: list[AtrasadoItemResponse]


class RankingItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    comision: str | None = None
    aprobadas_count: int


class RankingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagination: PaginationResponse
    items: list[RankingItemResponse]


class MateriaResumenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["sin_datos", "sin_actividades", "ok"]
    alumnos_activos: int
    actividades_analizadas: int
    aprobaciones_total: int
    alumnos_atrasados: int


class NotaFinalActividadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actividad: str
    nota_numerica: Decimal | None = None
    nota_textual: str | None = None


class NotaFinalItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    comision: str | None = None
    nota_final: Decimal | None = None
    tiene_nota_final: bool
    actividades: list[NotaFinalActividadResponse]


class NotasFinalesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NotaFinalItemResponse]


class MonitorItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    comision: str | None = None
    regional: str | None = None
    aprobadas_count: int
    actividades_pendientes: int
    estado: Literal["atrasado", "al_dia", "sin_actividades"]
    ultima_actividad_at: date | None = None


class MonitorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagination: PaginationResponse
    items: list[MonitorItemResponse]
