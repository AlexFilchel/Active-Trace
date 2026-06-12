from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntradaPadronItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    usuario_id: uuid.UUID | None
    nombre: str
    apellidos: str
    email: str
    comision: str | None
    regional: str | None


class PadronActivoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: uuid.UUID | None
    cargado_at: datetime | None
    entradas: list[EntradaPadronItem]


class CargarPadronResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: uuid.UUID
    entradas_cargadas: int
    version_anterior_desactivada: bool


class DescartePadronResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entradas_descartadas: int


class CargarMoodleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    moodle_course_id: int
