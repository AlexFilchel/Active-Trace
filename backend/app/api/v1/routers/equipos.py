from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.equipos import (
    AsignacionMasivaRequest,
    AsignacionMasivaResponse,
    ClonarEquipoRequest,
    ClonarEquipoResponse,
    DocenteBusquedaItem,
    MisEquiposItem,
    VigenciaEquipoRequest,
    VigenciaEquipoResponse,
)
from app.schemas.usuarios import AsignacionResponse
from app.services.equipo_service import EquipoService
from app.services.usuarios import ConflictError, NotFoundError

router = APIRouter(prefix="/api/equipos", tags=["equipos"])

RequiereEquipos = Annotated[AuthenticatedUser, require_permission("equipos:asignar")]


def _build_service(user: AuthenticatedUser, db: AsyncSession) -> EquipoService:
    return EquipoService(session=db, tenant_id=user.tenant_id)


def _handle_service_error(exc: Exception) -> None:
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    raise exc


@router.get("/mis-equipos", response_model=list[MisEquiposItem])
async def mis_equipos(
    user: RequiereEquipos,
    db: AsyncSession = Depends(get_db),
) -> list[MisEquiposItem]:
    service = _build_service(user, db)
    return await service.get_mis_equipos(auth_user_id=user.user_id)


@router.get("/asignaciones", response_model=list[AsignacionResponse])
async def listar_asignaciones_equipo(
    user: RequiereEquipos,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
    rol_id: uuid.UUID | None = Query(default=None),
    usuario_id: uuid.UUID | None = Query(default=None),
    active_only: bool = Query(default=False),
) -> list[AsignacionResponse]:
    service = _build_service(user, db)
    asignaciones = await service.list_asignaciones(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        rol_id=rol_id,
        usuario_id=usuario_id,
        active_only=active_only,
    )
    return [AsignacionResponse.model_validate(a, from_attributes=True) for a in asignaciones]


@router.get("/docentes/buscar", response_model=list[DocenteBusquedaItem])
async def buscar_docentes(
    user: RequiereEquipos,
    db: AsyncSession = Depends(get_db),
    q: str = Query(min_length=1),
) -> list[DocenteBusquedaItem]:
    service = _build_service(user, db)
    return await service.buscar_docentes(q)


@router.post("/asignaciones/masiva", response_model=AsignacionMasivaResponse, status_code=status.HTTP_201_CREATED)
async def asignacion_masiva(
    payload: AsignacionMasivaRequest,
    user: RequiereEquipos,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AsignacionMasivaResponse:
    service = _build_service(user, db)
    try:
        ip = request.client.host if request.client else None
        creadas = await service.asignacion_masiva(
            actor_id=user.user_id,
            payload=payload,
            ip=ip,
        )
        await db.commit()
        return AsignacionMasivaResponse(asignaciones_creadas=creadas)
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@router.post("/clonar", response_model=ClonarEquipoResponse, status_code=status.HTTP_201_CREATED)
async def clonar_equipo(
    payload: ClonarEquipoRequest,
    user: RequiereEquipos,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ClonarEquipoResponse:
    service = _build_service(user, db)
    try:
        ip = request.client.host if request.client else None
        clonadas = await service.clonar_equipo(
            actor_id=user.user_id,
            payload=payload,
            ip=ip,
        )
        await db.commit()
        return ClonarEquipoResponse(asignaciones_clonadas=clonadas)
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@router.patch("/vigencia", response_model=VigenciaEquipoResponse)
async def modificar_vigencia_equipo(
    payload: VigenciaEquipoRequest,
    user: RequiereEquipos,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> VigenciaEquipoResponse:
    service = _build_service(user, db)
    try:
        ip = request.client.host if request.client else None
        actualizadas = await service.modificar_vigencia_equipo(
            actor_id=user.user_id,
            payload=payload,
            ip=ip,
        )
        await db.commit()
        return VigenciaEquipoResponse(asignaciones_actualizadas=actualizadas)
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@router.get("/exportar")
async def exportar_equipo(
    user: RequiereEquipos,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
) -> StreamingResponse:
    service = _build_service(user, db)
    csv_content = await service.exportar_equipo(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=equipo-docente.csv"},
    )
