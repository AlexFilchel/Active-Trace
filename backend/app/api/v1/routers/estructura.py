"""Router de estructura académica: Carrera, Cohorte, Materia.

Todos los endpoints requieren permiso 'estructura:gestionar'.
Identidad y tenant se resuelven SIEMPRE desde el JWT verificado.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.estructura import (
    CarreraCreate, CarreraResponse, CarreraUpdate,
    CohorteCreate, CohorteResponse, CohorteUpdate,
    MateriaCreate, MateriaResponse, MateriaUpdate,
)
from app.services.estructura import (
    EstructuraService,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)


router = APIRouter(prefix="/api/admin", tags=["estructura"])

RequiereGestion = Annotated[AuthenticatedUser, require_permission("estructura:gestionar")]


def _build_service(user: AuthenticatedUser, db: AsyncSession) -> EstructuraService:
    return EstructuraService(session=db, tenant_id=user.tenant_id)


def _handle_service_error(exc: Exception) -> None:
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    if isinstance(exc, BusinessRuleError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.detail)
    raise exc


# ---------------------------------------------------------------------------
# Carreras
# ---------------------------------------------------------------------------

@router.get("/carreras", response_model=list[CarreraResponse])
async def listar_carreras(
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> list[CarreraResponse]:
    svc = _build_service(user, db)
    return await svc.listar_carreras()


@router.post("/carreras", response_model=CarreraResponse, status_code=status.HTTP_201_CREATED)
async def crear_carrera(
    payload: CarreraCreate,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> CarreraResponse:
    svc = _build_service(user, db)
    try:
        carrera = await svc.crear_carrera(codigo=payload.codigo, nombre=payload.nombre)
        await db.commit()
        await db.refresh(carrera)
        return carrera
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.get("/carreras/{carrera_id}", response_model=CarreraResponse)
async def obtener_carrera(
    carrera_id: uuid.UUID,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> CarreraResponse:
    svc = _build_service(user, db)
    try:
        return await svc.obtener_carrera(carrera_id)
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.patch("/carreras/{carrera_id}", response_model=CarreraResponse)
async def actualizar_carrera(
    carrera_id: uuid.UUID,
    payload: CarreraUpdate,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> CarreraResponse:
    svc = _build_service(user, db)
    fields = payload.model_dump(exclude_none=True)
    try:
        carrera = await svc.actualizar_carrera(carrera_id, **fields)
        await db.commit()
        await db.refresh(carrera)
        return carrera
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.delete("/carreras/{carrera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_carrera(
    carrera_id: uuid.UUID,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = _build_service(user, db)
    try:
        await svc.eliminar_carrera(carrera_id)
        await db.commit()
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


# ---------------------------------------------------------------------------
# Cohortes
# ---------------------------------------------------------------------------

@router.get("/cohortes", response_model=list[CohorteResponse])
async def listar_cohortes(
    user: RequiereGestion,
    carrera_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[CohorteResponse]:
    svc = _build_service(user, db)
    return await svc.listar_cohortes(carrera_id=carrera_id)


@router.post("/cohortes", response_model=CohorteResponse, status_code=status.HTTP_201_CREATED)
async def crear_cohorte(
    payload: CohorteCreate,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> CohorteResponse:
    svc = _build_service(user, db)
    try:
        cohorte = await svc.crear_cohorte(
            carrera_id=payload.carrera_id,
            nombre=payload.nombre,
            anio=payload.anio,
            vig_desde=payload.vig_desde,
            vig_hasta=payload.vig_hasta,
        )
        await db.commit()
        await db.refresh(cohorte)
        return cohorte
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.get("/cohortes/{cohorte_id}", response_model=CohorteResponse)
async def obtener_cohorte(
    cohorte_id: uuid.UUID,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> CohorteResponse:
    svc = _build_service(user, db)
    try:
        return await svc.obtener_cohorte(cohorte_id)
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.patch("/cohortes/{cohorte_id}", response_model=CohorteResponse)
async def actualizar_cohorte(
    cohorte_id: uuid.UUID,
    payload: CohorteUpdate,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> CohorteResponse:
    svc = _build_service(user, db)
    fields = payload.model_dump(exclude_none=True)
    try:
        cohorte = await svc.actualizar_cohorte(cohorte_id, **fields)
        await db.commit()
        await db.refresh(cohorte)
        return cohorte
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.delete("/cohortes/{cohorte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_cohorte(
    cohorte_id: uuid.UUID,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = _build_service(user, db)
    try:
        await svc.eliminar_cohorte(cohorte_id)
        await db.commit()
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


# ---------------------------------------------------------------------------
# Materias
# ---------------------------------------------------------------------------

@router.get("/materias", response_model=list[MateriaResponse])
async def listar_materias(
    user: RequiereGestion,
    estado: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[MateriaResponse]:
    svc = _build_service(user, db)
    return await svc.listar_materias(estado=estado)


@router.post("/materias", response_model=MateriaResponse, status_code=status.HTTP_201_CREATED)
async def crear_materia(
    payload: MateriaCreate,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> MateriaResponse:
    svc = _build_service(user, db)
    try:
        materia = await svc.crear_materia(codigo=payload.codigo, nombre=payload.nombre)
        await db.commit()
        await db.refresh(materia)
        return materia
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.get("/materias/{materia_id}", response_model=MateriaResponse)
async def obtener_materia(
    materia_id: uuid.UUID,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> MateriaResponse:
    svc = _build_service(user, db)
    try:
        return await svc.obtener_materia(materia_id)
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.patch("/materias/{materia_id}", response_model=MateriaResponse)
async def actualizar_materia(
    materia_id: uuid.UUID,
    payload: MateriaUpdate,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> MateriaResponse:
    svc = _build_service(user, db)
    fields = payload.model_dump(exclude_none=True)
    try:
        materia = await svc.actualizar_materia(materia_id, **fields)
        await db.commit()
        await db.refresh(materia)
        return materia
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)


@router.delete("/materias/{materia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_materia(
    materia_id: uuid.UUID,
    user: RequiereGestion,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = _build_service(user, db)
    try:
        await svc.eliminar_materia(materia_id)
        await db.commit()
    except (ConflictError, NotFoundError, BusinessRuleError) as exc:
        _handle_service_error(exc)
