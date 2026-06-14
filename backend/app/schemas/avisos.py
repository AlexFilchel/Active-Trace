from __future__ import annotations

from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


_ALCANCES = Literal["Global", "PorMateria", "PorCohorte", "PorRol"]
_SEVERIDADES = Literal["Info", "Advertencia", "Crítico"]


class CrearAvisoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    alcance: _ALCANCES
    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    rol_destino: str | None = None
    severidad: _SEVERIDADES = "Info"
    titulo: str = Field(min_length=1, max_length=255)
    cuerpo: str = Field(min_length=1)
    inicio_en: datetime
    fin_en: datetime
    orden: int = 0
    activo: bool = True
    requiere_ack: bool = False

    @model_validator(mode="after")
    def validar_fin_posterior_a_inicio(self) -> "CrearAvisoRequest":
        if self.fin_en <= self.inicio_en:
            raise ValueError("fin_en debe ser posterior a inicio_en")
        return self


class EditarAvisoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    alcance: _ALCANCES | None = None
    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    rol_destino: str | None = None
    severidad: _SEVERIDADES | None = None
    titulo: str | None = Field(default=None, min_length=1, max_length=255)
    cuerpo: str | None = Field(default=None, min_length=1)
    inicio_en: datetime | None = None
    fin_en: datetime | None = None
    orden: int | None = None
    activo: bool | None = None
    requiere_ack: bool | None = None

    @model_validator(mode="after")
    def validar_fin_posterior_a_inicio(self) -> "EditarAvisoRequest":
        if self.fin_en is not None and self.inicio_en is not None:
            if self.fin_en <= self.inicio_en:
                raise ValueError("fin_en debe ser posterior a inicio_en")
        return self


class AvisoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    alcance: str
    materia_id: uuid.UUID | None
    cohorte_id: uuid.UUID | None
    rol_destino: str | None
    severidad: str
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int
    activo: bool
    requiere_ack: bool
    created_at: datetime
    acusado: bool = False


class AvisoGestionResponse(AvisoResponse):
    total_acks: int = 0


class AckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aviso_id: uuid.UUID
    usuario_id: uuid.UUID
    confirmado_at: datetime
    ya_existia: bool


class MetricasAvisoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aviso_id: uuid.UUID
    titulo: str
    requiere_ack: bool
    total_acks: int
