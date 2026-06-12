from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.calificaciones import (
    ImportarRequest,
    ImportarResponse,
    PreviewResponse,
    ReporteFinalizacionResponse,
    UmbralRequest,
    UmbralResponse,
    VaciadoResponse,
)
from app.services.calificacion_service import CalificacionError, CalificacionService, UmbralService

router = APIRouter(prefix="/api/calificaciones", tags=["calificaciones"])

RequiereCalificaciones = Annotated[AuthenticatedUser, require_permission("calificaciones:importar")]

_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _build_service(user: AuthenticatedUser, db: AsyncSession) -> CalificacionService:
    return CalificacionService(session=db, tenant_id=user.tenant_id)


def _build_umbral_service(user: AuthenticatedUser, db: AsyncSession) -> UmbralService:
    return UmbralService(session=db, tenant_id=user.tenant_id)


@router.post("/preview", response_model=PreviewResponse)
async def preview_calificaciones(
    file: UploadFile,
    user: RequiereCalificaciones = None,
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    content = await file.read(_MAX_UPLOAD_SIZE)
    service = _build_service(user, db)
    return await service.preview(content=content, filename=file.filename or "upload.xlsx")


@router.post("/importar", response_model=ImportarResponse, status_code=status.HTTP_201_CREATED)
async def importar_calificaciones(
    file: UploadFile,
    materia_id: uuid.UUID = Query(...),
    actividades: list[str] = Query(default=[]),
    user: RequiereCalificaciones = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> ImportarResponse:
    content = await file.read(_MAX_UPLOAD_SIZE)
    service = _build_service(user, db)
    try:
        result = await service.importar(
            auth_user_id=user.user_id,
            materia_id=materia_id,
            actividades_seleccionadas=actividades,
            content=content,
            filename=file.filename or "upload.xlsx",
            ip=request.client.host if request and request.client else None,
        )
        await db.commit()
        return result
    except CalificacionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)


@router.post("/reporte-finalizacion", response_model=ReporteFinalizacionResponse)
async def reporte_finalizacion(
    version_id: uuid.UUID = Query(...),
    actividades_textuales: list[str] = Query(default=[]),
    user: RequiereCalificaciones = None,
    db: AsyncSession = Depends(get_db),
) -> ReporteFinalizacionResponse:
    service = _build_service(user, db)
    return await service.reporte_finalizacion(
        version_id=version_id,
        actividades_textuales=actividades_textuales,
    )


@router.delete("", response_model=VaciadoResponse)
async def vaciar_calificaciones(
    materia_id: uuid.UUID = Query(...),
    user: RequiereCalificaciones = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> VaciadoResponse:
    service = _build_service(user, db)
    try:
        result = await service.vaciar(
            auth_user_id=user.user_id,
            materia_id=materia_id,
            ip=request.client.host if request and request.client else None,
        )
        await db.commit()
        return result
    except CalificacionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)


@router.get("/umbral", response_model=UmbralResponse)
async def get_umbral(
    materia_id: uuid.UUID = Query(...),
    user: RequiereCalificaciones = None,
    db: AsyncSession = Depends(get_db),
) -> UmbralResponse:
    service = _build_umbral_service(user, db)
    try:
        return await service.get_umbral(auth_user_id=user.user_id, materia_id=materia_id)
    except CalificacionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)


@router.put("/umbral", response_model=UmbralResponse)
async def set_umbral(
    payload: UmbralRequest,
    materia_id: uuid.UUID = Query(...),
    user: RequiereCalificaciones = None,
    db: AsyncSession = Depends(get_db),
) -> UmbralResponse:
    service = _build_umbral_service(user, db)
    try:
        result = await service.set_umbral(
            auth_user_id=user.user_id,
            materia_id=materia_id,
            request=payload,
        )
        await db.commit()
        return result
    except CalificacionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)
