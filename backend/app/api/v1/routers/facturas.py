from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.liquidaciones import CrearFacturaRequest, FacturaResponse
from app.services.factura_service import FacturaService

router = APIRouter(prefix="/api/facturas", tags=["facturas"])

RequiereGestionar = Annotated[AuthenticatedUser, require_permission("liquidaciones:gestionar-facturas")]


def _svc(user: AuthenticatedUser, db: AsyncSession) -> FacturaService:
    return FacturaService(session=db, tenant_id=user.tenant_id)


@router.post("", response_model=FacturaResponse, status_code=201)
async def crear_factura(
    payload: CrearFacturaRequest,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> FacturaResponse:
    factura = await _svc(user, db).crear(payload=payload, actor_id=user.user_id)
    await db.commit()
    return FacturaResponse.model_validate(factura, from_attributes=True)


@router.get("", response_model=list[FacturaResponse])
async def listar_facturas(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    usuario_id: uuid.UUID | None = None,
    estado: str | None = None,
    periodo: str | None = None,
) -> list[FacturaResponse]:
    items = await _svc(user, db).listar(usuario_id=usuario_id, estado=estado, periodo=periodo)
    return [FacturaResponse.model_validate(i, from_attributes=True) for i in items]


@router.patch("/{factura_id}/abonar", response_model=FacturaResponse)
async def abonar_factura(
    factura_id: uuid.UUID,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> FacturaResponse:
    factura = await _svc(user, db).abonar(factura_id=factura_id, actor_id=user.user_id)
    await db.commit()
    return FacturaResponse.model_validate(factura, from_attributes=True)
