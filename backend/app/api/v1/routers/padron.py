from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.integrations.moodle_ws import MoodleWSError
from app.schemas.padron import (
    CargarMoodleRequest,
    CargarPadronResponse,
    DescartePadronResponse,
    PadronActivoResponse,
)
from app.services.padron_parser import ParseError
from app.services.padron_service import NotFoundError, PadronService

router = APIRouter(prefix="/api/padron", tags=["padron"])

RequierePadron = Annotated[AuthenticatedUser, require_permission("padron:gestionar")]

_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _build_service(user: AuthenticatedUser, db: AsyncSession) -> PadronService:
    return PadronService(session=db, tenant_id=user.tenant_id)


@router.post("/cargar", response_model=CargarPadronResponse, status_code=status.HTTP_201_CREATED)
async def cargar_padron(
    file: UploadFile,
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    user: RequierePadron = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> CargarPadronResponse:
    content = await file.read(_MAX_UPLOAD_SIZE)
    service = _build_service(user, db)
    try:
        result = await service.cargar_desde_archivo(
            actor_id=user.user_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            content=content,
            filename=file.filename or "upload.csv",
            ip=request.client.host if request and request.client else None,
        )
        await db.commit()
        return result
    except ParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)


@router.post("/cargar-moodle", response_model=CargarPadronResponse, status_code=status.HTTP_201_CREATED)
async def cargar_padron_moodle(
    payload: CargarMoodleRequest,
    user: RequierePadron = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> CargarPadronResponse:
    service = _build_service(user, db)
    try:
        result = await service.cargar_desde_moodle(
            actor_id=user.user_id,
            materia_id=payload.materia_id,
            cohorte_id=payload.cohorte_id,
            moodle_course_id=payload.moodle_course_id,
            ip=request.client.host if request and request.client else None,
        )
        await db.commit()
        return result
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)
    except MoodleWSError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/activo", response_model=PadronActivoResponse)
async def get_padron_activo(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    user: RequierePadron = None,
    db: AsyncSession = Depends(get_db),
) -> PadronActivoResponse:
    service = _build_service(user, db)
    return await service.get_padron_activo(materia_id, cohorte_id)


@router.delete("/activo", response_model=DescartePadronResponse)
async def descartar_padron(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    user: RequierePadron = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> DescartePadronResponse:
    service = _build_service(user, db)
    try:
        result = await service.descartar_padron(
            actor_id=user.user_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            ip=request.client.host if request and request.client else None,
        )
        await db.commit()
        return result
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
