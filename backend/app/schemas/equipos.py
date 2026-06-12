from __future__ import annotations

from datetime import date
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EstadoVigencia = Literal["Vigente", "Vencida", "Futura"]


class MisEquiposItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    usuario_id: uuid.UUID
    rol_id: uuid.UUID
    rol_nombre: str | None = None
    materia_id: uuid.UUID | None = None
    materia_nombre: str | None = None
    carrera_id: uuid.UUID | None = None
    carrera_nombre: str | None = None
    cohorte_id: uuid.UUID | None = None
    cohorte_nombre: str | None = None
    comisiones: list[str]
    desde: date
    hasta: date | None = None
    estado_vigencia: EstadoVigencia


class AsignacionMasivaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_ids: list[uuid.UUID] = Field(min_length=1)
    rol_id: uuid.UUID
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None
    comisiones: list[str] = Field(default_factory=list)
    desde: date
    hasta: date | None = None


class AsignacionMasivaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asignaciones_creadas: int


class OrigenEquipo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID


class DestinoEquipo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    desde: date
    hasta: date | None = None


class ClonarEquipoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origen: OrigenEquipo
    destino: DestinoEquipo


class ClonarEquipoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asignaciones_clonadas: int


class VigenciaEquipoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    desde: date
    hasta: date | None = None


class VigenciaEquipoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asignaciones_actualizadas: int


class DocenteBusquedaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    nombre: str
    apellidos: str
    legajo: str | None = None


class ExportarEquipoQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
