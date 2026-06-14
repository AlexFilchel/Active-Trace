from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.programas import (
    CrearFechaAcademicaRequest,
    CrearProgramaRequest,
    EditarFechaAcademicaRequest,
    FechaAcademicaResponse,
    FragmentoLmsResponse,
    ProgramaResponse,
)
from app.services.programa_service import FechaAcademicaNotFoundError, ProgramaService


programas_router = APIRouter(prefix="/api/programas", tags=["programas"])
fechas_router = APIRouter(prefix="/api/fechas-academicas", tags=["fechas-academicas"])

RequiereGestionar = Annotated[AuthenticatedUser, require_permission("estructura:gestionar")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> ProgramaService:
    return ProgramaService(session=db, tenant_id=user.tenant_id)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# Programas
# ---------------------------------------------------------------------------

@programas_router.post("", status_code=status.HTTP_201_CREATED, response_model=ProgramaResponse)
async def crear_programa(
    payload: CrearProgramaRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProgramaResponse:
    result = await _service(user, db).crear_programa(
        actor_id=user.user_id,
        payload=payload,
        ip=_ip(request),
    )
    await db.commit()
    return result


@programas_router.get("", response_model=list[ProgramaResponse])
async def listar_programas(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
) -> list[ProgramaResponse]:
    return await _service(user, db).listar_programas(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# Fechas académicas — /fragmento-lms BEFORE /{id}
# ---------------------------------------------------------------------------

@fechas_router.get("/fragmento-lms", response_model=FragmentoLmsResponse)
async def generar_fragmento_lms(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    periodo: str = Query(...),
) -> FragmentoLmsResponse:
    return await _service(user, db).generar_fragmento_lms(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        periodo=periodo,
    )


@fechas_router.post("", status_code=status.HTTP_201_CREATED, response_model=FechaAcademicaResponse)
async def crear_fecha(
    payload: CrearFechaAcademicaRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FechaAcademicaResponse:
    result = await _service(user, db).crear_fecha(
        actor_id=user.user_id,
        payload=payload,
        ip=_ip(request),
    )
    await db.commit()
    return result


@fechas_router.get("", response_model=list[FechaAcademicaResponse])
async def listar_fechas(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
    tipo: str | None = Query(default=None),
    periodo: str | None = Query(default=None),
) -> list[FechaAcademicaResponse]:
    return await _service(user, db).listar_fechas(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        periodo=periodo,
    )


@fechas_router.patch("/{fecha_id}", response_model=FechaAcademicaResponse)
async def editar_fecha(
    fecha_id: uuid.UUID,
    payload: EditarFechaAcademicaRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FechaAcademicaResponse:
    try:
        result = await _service(user, db).editar_fecha(
            actor_id=user.user_id,
            fecha_id=fecha_id,
            payload=payload,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except FechaAcademicaNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
