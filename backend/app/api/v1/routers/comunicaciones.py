from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.comunicaciones import ApprovalResponse, CancelResponse, ComunicacionItemResponse, EnqueueRequest, EnqueueResponse, PreviewRequest, PreviewResponse
from app.services.comunicaciones import CommunicationError, ComunicacionService


router = APIRouter(prefix="/api/comunicaciones", tags=["comunicaciones"])
RequiereEnviar = Annotated[AuthenticatedUser, require_permission("comunicacion:enviar")]
RequiereAprobar = Annotated[AuthenticatedUser, require_permission("comunicacion:aprobar")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> ComunicacionService:
    return ComunicacionService(session=db, tenant_id=user.tenant_id)


def _raise_service_error(exc: CommunicationError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/preview", response_model=PreviewResponse)
async def preview(payload: PreviewRequest, user: RequiereEnviar, db: AsyncSession = Depends(get_db)) -> PreviewResponse:
    try:
        return PreviewResponse.model_validate(await _service(user, db).preview(user=user, **payload.model_dump()))
    except CommunicationError as exc:
        _raise_service_error(exc)


@router.post("/enqueue", response_model=EnqueueResponse, status_code=status.HTTP_201_CREATED)
async def enqueue(payload: EnqueueRequest, user: RequiereEnviar, db: AsyncSession = Depends(get_db), response: Response = None) -> EnqueueResponse:
    try:
        result = await _service(user, db).enqueue(user=user, **payload.model_dump())
        await db.commit()
        if result["reused"]:
            if response is not None:
                response.status_code = status.HTTP_200_OK
            return EnqueueResponse.model_validate(result)
        return EnqueueResponse.model_validate(result)
    except CommunicationError as exc:
        await db.rollback()
        _raise_service_error(exc)


@router.post("/lotes/{lote_id}/approve", response_model=ApprovalResponse)
async def approve_lote(lote_id: uuid.UUID, user: RequiereAprobar, db: AsyncSession = Depends(get_db)) -> ApprovalResponse:
    approved = await _service(user, db).approve_lote(user=user, lote_id=lote_id)
    await db.commit()
    return ApprovalResponse(aprobadas=approved)


@router.post("/{comunicacion_id}/approve", response_model=ApprovalResponse)
async def approve_one(comunicacion_id: uuid.UUID, user: RequiereAprobar, db: AsyncSession = Depends(get_db)) -> ApprovalResponse:
    try:
        approved = await _service(user, db).approve_one(user=user, comunicacion_id=comunicacion_id)
        await db.commit()
        return ApprovalResponse(aprobadas=approved)
    except CommunicationError as exc:
        await db.rollback()
        _raise_service_error(exc)


@router.post("/{comunicacion_id}/cancel", response_model=CancelResponse)
async def cancel(comunicacion_id: uuid.UUID, user: RequiereEnviar, db: AsyncSession = Depends(get_db)) -> CancelResponse:
    try:
        row = await _service(user, db).cancel(user=user, comunicacion_id=comunicacion_id)
        await db.commit()
        return CancelResponse(id=row.id, estado=row.estado)
    except CommunicationError as exc:
        await db.rollback()
        _raise_service_error(exc)


@router.get("", response_model=list[ComunicacionItemResponse])
async def list_items(user: RequiereEnviar, db: AsyncSession = Depends(get_db)) -> list[ComunicacionItemResponse]:
    return [ComunicacionItemResponse.model_validate(item) for item in await _service(user, db).list_items()]
