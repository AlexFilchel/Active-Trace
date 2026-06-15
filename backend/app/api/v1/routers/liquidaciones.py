from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.repositories.liquidaciones import LiquidacionRepository
from app.schemas.liquidaciones import (
    CalcularLiquidacionRequest,
    LiquidacionKpisResponse,
    LiquidacionResponse,
)
from app.services.liquidacion_service import LiquidacionService

router = APIRouter(prefix="/api/liquidaciones", tags=["liquidaciones"])

RequiereVer = Annotated[AuthenticatedUser, require_permission("liquidaciones:ver")]
RequiereCerrar = Annotated[AuthenticatedUser, require_permission("liquidaciones:cerrar")]


def _svc(user: AuthenticatedUser, db: AsyncSession) -> LiquidacionService:
    return LiquidacionService(session=db, tenant_id=user.tenant_id)


@router.post("/calcular", response_model=list[LiquidacionResponse], status_code=201)
async def calcular_liquidacion(
    payload: CalcularLiquidacionRequest,
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
) -> list[LiquidacionResponse]:
    liquidaciones = await _svc(user, db).calcular(
        cohorte_id=payload.cohorte_id,
        periodo=payload.periodo,
        actor_id=user.user_id,
    )
    await db.commit()
    return [LiquidacionResponse.model_validate(l, from_attributes=True) for l in liquidaciones]


@router.get("", response_model=list[LiquidacionResponse])
async def listar_liquidaciones(
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
    cohorte_id: uuid.UUID | None = None,
    periodo: str | None = None,
    estado: str | None = None,
    usuario_id: uuid.UUID | None = None,
) -> list[LiquidacionResponse]:
    repo = LiquidacionRepository(session=db, tenant_id=user.tenant_id)
    items = await repo.listar(cohorte_id=cohorte_id, periodo=periodo, estado=estado, usuario_id=usuario_id)
    return [LiquidacionResponse.model_validate(i, from_attributes=True) for i in items]


@router.get("/{cohorte_id}/{periodo}/kpis", response_model=LiquidacionKpisResponse)
async def kpis_liquidacion(
    cohorte_id: uuid.UUID,
    periodo: str,
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
) -> LiquidacionKpisResponse:
    return await _svc(user, db).kpis(cohorte_id=cohorte_id, periodo=periodo)


@router.post("/{cohorte_id}/{periodo}/cerrar", status_code=200)
async def cerrar_liquidacion(
    cohorte_id: uuid.UUID,
    periodo: str,
    user: RequiereCerrar,
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await _svc(user, db).cerrar(
        cohorte_id=cohorte_id,
        periodo=periodo,
        actor_id=user.user_id,
    )
    await db.commit()
    return {"cerradas": count, "cohorte_id": str(cohorte_id), "periodo": periodo}


@router.get("/historial", response_model=list[LiquidacionResponse])
async def historial_liquidaciones(
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
    cohorte_id: uuid.UUID | None = None,
) -> list[LiquidacionResponse]:
    repo = LiquidacionRepository(session=db, tenant_id=user.tenant_id)
    items = await repo.listar(cohorte_id=cohorte_id, estado="Cerrada")
    return [LiquidacionResponse.model_validate(i, from_attributes=True) for i in items]
