from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.encuentros import (
    BloqueHtmlResponse,
    CrearRecurrenteRequest,
    CrearUnicoRequest,
    EditarInstanciaRequest,
    InstanciaEncuentroResponse,
    SlotEncuentroResponse,
)
from app.services.encuentro_service import EncuentroNotFoundError, EncuentroService


router = APIRouter(prefix="/api/encuentros", tags=["encuentros"])
RequiereGestionar = Annotated[AuthenticatedUser, require_permission("encuentros:gestionar")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> EncuentroService:
    return EncuentroService(session=db, tenant_id=user.tenant_id)


@router.post("/recurrente", status_code=status.HTTP_201_CREATED)
async def crear_recurrente(
    payload: CrearRecurrenteRequest,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        slot, instancias = await _service(user, db).crear_recurrente(
            actor_id=user.user_id,
            payload=payload,
        )
        await db.commit()
        return {
            "slot": SlotEncuentroResponse.model_validate(slot),
            "instancias_creadas": len(instancias),
        }
    except EncuentroNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/unico", status_code=status.HTTP_201_CREATED)
async def crear_unico(
    payload: CrearUnicoRequest,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        slot, instancia = await _service(user, db).crear_unico(
            actor_id=user.user_id,
            payload=payload,
        )
        await db.commit()
        return {
            "slot": SlotEncuentroResponse.model_validate(slot),
            "instancia": InstanciaEncuentroResponse.model_validate(instancia),
        }
    except EncuentroNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.patch("/instancias/{instancia_id}", response_model=InstanciaEncuentroResponse)
async def editar_instancia(
    instancia_id: uuid.UUID,
    payload: EditarInstanciaRequest,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> InstanciaEncuentroResponse:
    try:
        instancia = await _service(user, db).editar_instancia(instancia_id, payload)
        await db.commit()
        return InstanciaEncuentroResponse.model_validate(instancia)
    except EncuentroNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("", response_model=list[InstanciaEncuentroResponse])
async def listar_encuentros(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = None,
    cohorte_id: uuid.UUID | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[InstanciaEncuentroResponse]:
    instancias = await _service(user, db).listar_encuentros(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        estado=estado,
        desde=desde,
        hasta=hasta,
    )
    return [InstanciaEncuentroResponse.model_validate(i) for i in instancias]


@router.get("/bloque-html", response_model=BloqueHtmlResponse)
async def bloque_html(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = None,
    cohorte_id: uuid.UUID | None = None,
) -> BloqueHtmlResponse:
    if materia_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="materia_id es requerido.")
    html_content = await _service(user, db).generar_bloque_html(materia_id, cohorte_id)
    return BloqueHtmlResponse(html=html_content)
