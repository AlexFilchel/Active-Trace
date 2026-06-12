from __future__ import annotations

from datetime import date, datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EstadoUsuario = Literal["Activo", "Inactivo"]
EstadoVigencia = Literal["Vigente", "Vencida", "Futura"]


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    auth_user_id: uuid.UUID | None = None
    nombre: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    dni: str | None = Field(default=None, max_length=64)
    cuil: str | None = Field(default=None, max_length=64)
    cbu: str | None = Field(default=None, max_length=64)
    alias_cbu: str | None = Field(default=None, max_length=120)
    banco: str | None = Field(default=None, max_length=120)
    regional: str | None = Field(default=None, max_length=120)
    legajo: str | None = Field(default=None, max_length=120)
    legajo_profesional: str | None = Field(default=None, max_length=120)
    facturador: bool = False
    estado: EstadoUsuario = "Activo"


class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    auth_user_id: uuid.UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellidos: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    dni: str | None = Field(default=None, max_length=64)
    cuil: str | None = Field(default=None, max_length=64)
    cbu: str | None = Field(default=None, max_length=64)
    alias_cbu: str | None = Field(default=None, max_length=120)
    banco: str | None = Field(default=None, max_length=120)
    regional: str | None = Field(default=None, max_length=120)
    legajo: str | None = Field(default=None, max_length=120)
    legajo_profesional: str | None = Field(default=None, max_length=120)
    facturador: bool | None = None
    estado: EstadoUsuario | None = None


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    auth_user_id: uuid.UUID | None = None
    nombre: str
    apellidos: str
    email: str
    dni: str | None = None
    cuil: str | None = None
    cbu: str | None = None
    alias_cbu: str | None = None
    banco: str | None = None
    regional: str | None = None
    legajo: str | None = None
    legajo_profesional: str | None = None
    facturador: bool
    estado: EstadoUsuario
    created_at: datetime
    updated_at: datetime


class AsignacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    usuario_id: uuid.UUID
    rol_id: uuid.UUID
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None
    comisiones: list[str] = Field(default_factory=list)
    desde: date
    hasta: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AsignacionCreate":
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("hasta must be greater than or equal to desde")
        return self


class AsignacionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    rol_id: uuid.UUID | None = None
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None
    comisiones: list[str] | None = None
    desde: date | None = None
    hasta: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AsignacionUpdate":
        if self.desde is not None and self.hasta is not None and self.hasta < self.desde:
            raise ValueError("hasta must be greater than or equal to desde")
        return self


class AsignacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    rol_id: uuid.UUID
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None
    comisiones: list[str]
    desde: date
    hasta: date | None = None
    estado_vigencia: EstadoVigencia
    created_at: datetime
    updated_at: datetime
