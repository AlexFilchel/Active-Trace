from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PerfilResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: uuid.UUID
    auth_user_id: uuid.UUID | None
    nombre: str
    apellidos: str
    email: str | None
    dni: str | None
    cuil: str | None
    cbu: str | None
    alias_cbu: str | None
    banco: str | None
    regional: str | None
    legajo: str | None
    legajo_profesional: str | None
    facturador: bool
    estado: str
    created_at: datetime
    updated_at: datetime


class PerfilUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellidos: str | None = Field(default=None, min_length=1, max_length=120)
    banco: str | None = Field(default=None, max_length=120)
    cbu: str | None = Field(default=None, max_length=512)
    alias_cbu: str | None = Field(default=None, max_length=512)
    regional: str | None = Field(default=None, max_length=120)
    legajo_profesional: str | None = Field(default=None, max_length=120)
    facturador: bool | None = None
