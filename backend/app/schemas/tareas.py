from __future__ import annotations

from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field


_ESTADOS = Literal["Pendiente", "En progreso", "Resuelta", "Cancelada"]


class CrearTareaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asignado_a: uuid.UUID
    descripcion: str = Field(min_length=1)
    materia_id: uuid.UUID | None = None
    contexto_id: uuid.UUID | None = None


class CambiarEstadoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: _ESTADOS


class TareaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID | None
    asignado_a: uuid.UUID
    asignado_por: uuid.UUID
    estado: str
    descripcion: str
    contexto_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CrearComentarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    texto: str = Field(min_length=1)


class ComentarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tarea_id: uuid.UUID
    autor_id: uuid.UUID
    texto: str
    comentado_at: datetime
