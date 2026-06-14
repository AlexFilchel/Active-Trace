from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.tareas import (
    CambiarEstadoRequest,
    ComentarioResponse,
    CrearComentarioRequest,
    CrearTareaRequest,
    TareaResponse,
)
from app.services.tarea_service import (
    TareaNotFoundError,
    TareaService,
    TareaTransicionInvalidaError,
)


router = APIRouter(prefix="/api/tareas", tags=["tareas"])

RequiereGestionar = Annotated[AuthenticatedUser, require_permission("tareas:gestionar")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> TareaService:
    return TareaService(session=db, tenant_id=user.tenant_id)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# CRITICAL: /mis-tareas MUST be registered BEFORE /{tarea_id}
# ---------------------------------------------------------------------------

@router.get("/mis-tareas", response_model=list[TareaResponse])
async def listar_mis_tareas(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    estado: str | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
) -> list[TareaResponse]:
    try:
        return await _service(user, db).listar_mis_tareas(
            auth_user_id=user.user_id,
            estado=estado,
            materia_id=materia_id,
        )
    except TareaNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("", response_model=list[TareaResponse])
async def listar_admin(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    asignado_a: uuid.UUID | None = Query(default=None),
    asignado_por: uuid.UUID | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    estado: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TareaResponse]:
    return await _service(user, db).listar_admin(
        asignado_a=asignado_a,
        asignado_por=asignado_por,
        materia_id=materia_id,
        estado=estado,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TareaResponse)
async def crear_tarea(
    payload: CrearTareaRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TareaResponse:
    try:
        result = await _service(user, db).crear_tarea(
            actor_auth_id=user.user_id,
            payload=payload,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except TareaNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.patch("/{tarea_id}/estado", response_model=TareaResponse)
async def cambiar_estado(
    tarea_id: uuid.UUID,
    payload: CambiarEstadoRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TareaResponse:
    try:
        result = await _service(user, db).cambiar_estado(
            actor_auth_id=user.user_id,
            tarea_id=tarea_id,
            nuevo_estado=payload.estado,
            roles=user.roles,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except TareaNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except TareaTransicionInvalidaError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "/{tarea_id}/comentarios",
    status_code=status.HTTP_201_CREATED,
    response_model=ComentarioResponse,
)
async def agregar_comentario(
    tarea_id: uuid.UUID,
    payload: CrearComentarioRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ComentarioResponse:
    try:
        result = await _service(user, db).agregar_comentario(
            actor_auth_id=user.user_id,
            tarea_id=tarea_id,
            payload=payload,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except TareaNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{tarea_id}/comentarios", response_model=list[ComentarioResponse])
async def listar_comentarios(
    tarea_id: uuid.UUID,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> list[ComentarioResponse]:
    try:
        return await _service(user, db).listar_comentarios(tarea_id=tarea_id)
    except TareaNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
