from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validar_periodo(v: str) -> str:
    if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
        raise ValueError("periodo debe tener formato AAAA-MM")
    return v


# ── Salario Base ─────────────────────────────────────────────────────────────

class CrearSalarioBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: str
    monto: Decimal = Field(gt=0)
    desde: date
    hasta: date | None = None


class EditarSalarioBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto: Decimal | None = Field(default=None, gt=0)
    hasta: date | None = None


class SalarioBaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    rol: str
    monto: Decimal
    desde: date
    hasta: date | None


# ── Salario Plus ─────────────────────────────────────────────────────────────

class CrearSalarioPlusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grupo: str = Field(min_length=1, max_length=50)
    rol: str
    descripcion: str | None = None
    monto: Decimal = Field(gt=0)
    desde: date
    hasta: date | None = None


class EditarSalarioPlusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str | None = None
    monto: Decimal | None = Field(default=None, gt=0)
    hasta: date | None = None


class SalarioPlusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    grupo: str
    rol: str
    descripcion: str | None
    monto: Decimal
    desde: date
    hasta: date | None


# ── Liquidación ───────────────────────────────────────────────────────────────

class CalcularLiquidacionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    periodo: str

    @field_validator("periodo")
    @classmethod
    def validar_periodo(cls, v: str) -> str:
        return _validar_periodo(v)


class LiquidacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cohorte_id: uuid.UUID
    periodo: str
    usuario_id: uuid.UUID
    rol: str
    comisiones: list | None
    monto_base: Decimal
    monto_plus: Decimal
    total: Decimal
    es_nexo: bool
    excluido_por_factura: bool
    estado: str


class LiquidacionKpisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    periodo: str
    estado: str | None
    total_sin_factura: Decimal
    total_con_factura: Decimal
    total_nexo: Decimal
    cantidad_docentes: int
    cantidad_facturantes: int


# ── Factura ───────────────────────────────────────────────────────────────────

class CrearFacturaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID
    periodo: str
    detalle: str | None = None
    referencia_archivo: str | None = None
    tamano_kb: Decimal | None = Field(default=None, ge=0)

    @field_validator("periodo")
    @classmethod
    def validar_periodo(cls, v: str) -> str:
        return _validar_periodo(v)


class FacturaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    periodo: str
    detalle: str | None
    referencia_archivo: str | None
    tamano_kb: Decimal | None
    estado: str
    cargada_at: datetime
    abonada_at: datetime | None
