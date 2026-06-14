from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AccionPorDiaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    total: int


class EstadoComunicacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: uuid.UUID
    accion: str
    total: int


class InteraccionDocenteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: uuid.UUID
    accion: str
    total: int


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    accion: str
    filas_afectadas: int
    detalle: dict | None
    ip: str | None
    fecha_hora: datetime
