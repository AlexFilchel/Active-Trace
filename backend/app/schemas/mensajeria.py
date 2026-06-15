from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CrearHiloRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destinatario_id: uuid.UUID
    asunto: str = Field(min_length=1, max_length=200)
    cuerpo: str = Field(min_length=1)


class ResponderHiloRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destinatario_id: uuid.UUID
    cuerpo: str = Field(min_length=1)


class MensajeInternoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    hilo_id: uuid.UUID
    remitente_id: uuid.UUID
    destinatario_id: uuid.UUID
    cuerpo: str
    leido: bool
    sent_at: datetime


class HiloMensajeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    asunto: str
    creado_por: uuid.UUID
    created_at: datetime
    mensajes_no_leidos: int = 0
    ultimo_mensaje: MensajeInternoResponse | None = None
