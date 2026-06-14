from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    materia_id: uuid.UUID
    destinatarios: list[uuid.UUID] = Field(min_length=1)
    asunto_template: str = Field(min_length=1, max_length=255)
    cuerpo_template: str = Field(min_length=1)


class PreviewItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    asunto: str
    cuerpo: str
    destinatario_masked: str


class PreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_token: str
    expires_at: datetime
    items: list[PreviewItemResponse]


class EnqueueRequest(PreviewRequest):
    idempotency_key: str = Field(min_length=1, max_length=128)
    preview_token: str = Field(min_length=1)


class ComunicacionItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    lote_id: uuid.UUID
    materia_id: uuid.UUID
    entrada_padron_id: uuid.UUID
    estado: str
    requiere_aprobacion: bool
    intentos: int
    destinatario_masked: str
    asunto: str
    created_at: datetime
    aprobado_at: datetime | None = None
    enviado_at: datetime | None = None
    cancelado_at: datetime | None = None


class EnqueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lote_id: uuid.UUID
    reused: bool
    comunicaciones: list[ComunicacionItemResponse]


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aprobadas: int


class CancelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    estado: str
