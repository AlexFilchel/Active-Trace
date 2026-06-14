from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CrearRecurrenteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    materia_id: uuid.UUID
    asignacion_id: uuid.UUID
    dia_semana: int = Field(ge=0, le=6, description="0=lunes … 6=domingo")
    hora: time
    fecha_inicio: date
    cant_semanas: int = Field(ge=1, le=52)
    titulo: str = Field(min_length=1, max_length=255)
    meet_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validar_dia_semana_fecha_inicio(self) -> "CrearRecurrenteRequest":
        if self.fecha_inicio.weekday() != self.dia_semana:
            raise ValueError(
                f"fecha_inicio ({self.fecha_inicio}) debe caer en el dia_semana indicado "
                f"({self.dia_semana}); el día de la semana es {self.fecha_inicio.weekday()}."
            )
        return self


class CrearUnicoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    materia_id: uuid.UUID
    asignacion_id: uuid.UUID
    fecha: date
    hora: time
    titulo: str = Field(min_length=1, max_length=255)
    meet_url: str | None = Field(default=None, max_length=500)


class EditarInstanciaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    estado: Literal["Programado", "Realizado", "Cancelado"] | None = None
    meet_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    comentario: str | None = None


class SlotEncuentroResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    titulo: str
    hora: time
    dia_semana: int
    fecha_inicio: date
    cant_semanas: int
    fecha_unica: date | None = None
    meet_url: str | None = None
    vig_desde: date | None = None
    vig_hasta: date | None = None
    created_at: datetime


class InstanciaEncuentroResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    slot_id: uuid.UUID | None = None
    materia_id: uuid.UUID
    fecha: date
    hora: time
    titulo: str
    estado: str
    meet_url: str | None = None
    video_url: str | None = None
    comentario: str | None = None
    created_at: datetime


class BloqueHtmlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    html: str
