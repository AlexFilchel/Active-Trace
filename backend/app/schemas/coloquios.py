from __future__ import annotations

from datetime import date, datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class DiaConvocatoriaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    cupo_total: int = Field(gt=0, description="Cupo por día, debe ser mayor que 0")


class CrearConvocatoriaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    instancia: str = Field(min_length=1, max_length=255)
    dias: list[DiaConvocatoriaIn] = Field(min_length=1, description="Al menos un día")


class EditarConvocatoriaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instancia: str | None = Field(default=None, min_length=1, max_length=255)
    estado: Literal["Abierta", "Cerrada"] | None = None


class ImportarCandidatosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno_ids: list[uuid.UUID] = Field(min_length=1)


class ReservarTurnoRequest(BaseModel):
    """El alumno_id se toma SIEMPRE de la sesión; no se acepta en el payload."""

    model_config = ConfigDict(extra="forbid")

    dia_evaluacion_id: uuid.UUID


class CancelarReservaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["Cancelada"]


class RegistrarResultadoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    alumno_id: uuid.UUID
    nota_final: str = Field(min_length=1, max_length=50)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DiaConvocatoriaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    fecha: date
    cupo_total: int


class ConvocatoriaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: str
    instancia: str
    dias_disponibles: int
    estado: str
    created_at: datetime
    # Métricas derivadas (calculadas en servicio, no en modelo)
    convocados: int = 0
    reservas_activas: int = 0
    cupos_libres: int = 0


class ReservaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    dia_evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    estado: str
    fecha_hora: datetime | None = None
    created_at: datetime


class ResultadoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    nota_final: str
    created_at: datetime


class MetricasResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    convocados: int
    instancias_activas: int
    reservas_activas: int
    notas_registradas: int


class AgendaDiaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    reservas: list[ReservaResponse]
