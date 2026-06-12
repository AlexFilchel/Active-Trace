from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.usuarios import AsignacionCreate, AsignacionResponse, AsignacionUpdate, UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services.usuarios import ConflictError, NotFoundError, UsuarioService


usuarios_router = APIRouter(prefix="/api/admin/usuarios", tags=["usuarios"])
asignaciones_router = APIRouter(prefix="/api/asignaciones", tags=["asignaciones"])

RequiereUsuarios = Annotated[AuthenticatedUser, require_permission("usuarios:gestionar")]
RequiereAsignaciones = Annotated[AuthenticatedUser, require_permission("equipos:asignar")]


def _build_service(user: AuthenticatedUser, db: AsyncSession) -> UsuarioService:
    return UsuarioService(session=db, tenant_id=user.tenant_id)


def _handle_service_error(exc: Exception) -> None:
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    raise exc


@usuarios_router.get("", response_model=list[UsuarioResponse])
async def listar_usuarios(user: RequiereUsuarios, db: AsyncSession = Depends(get_db)) -> list[UsuarioResponse]:
    service = _build_service(user, db)
    payload = await service.serialize_usuarios_response(await service.listar_usuarios())
    return [UsuarioResponse.model_validate(item) for item in payload]


@usuarios_router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(payload: UsuarioCreate, user: RequiereUsuarios, db: AsyncSession = Depends(get_db)) -> UsuarioResponse:
    service = _build_service(user, db)
    try:
        usuario = await service.crear_usuario(**payload.model_dump())
        await db.commit()
        await db.refresh(usuario)
        return UsuarioResponse.model_validate(await service.serialize_usuario_response(usuario))
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@usuarios_router.get("/{usuario_id}", response_model=UsuarioResponse)
async def obtener_usuario(usuario_id: uuid.UUID, user: RequiereUsuarios, db: AsyncSession = Depends(get_db)) -> UsuarioResponse:
    service = _build_service(user, db)
    try:
        return UsuarioResponse.model_validate(await service.serialize_usuario_response(await service.obtener_usuario(usuario_id)))
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@usuarios_router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def actualizar_usuario(usuario_id: uuid.UUID, payload: UsuarioUpdate, user: RequiereUsuarios, db: AsyncSession = Depends(get_db)) -> UsuarioResponse:
    service = _build_service(user, db)
    try:
        usuario = await service.actualizar_usuario(usuario_id, **payload.model_dump(exclude_unset=True))
        await db.commit()
        await db.refresh(usuario)
        return UsuarioResponse.model_validate(await service.serialize_usuario_response(usuario))
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@usuarios_router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(usuario_id: uuid.UUID, user: RequiereUsuarios, db: AsyncSession = Depends(get_db)) -> None:
    service = _build_service(user, db)
    try:
        await service.eliminar_usuario(usuario_id)
        await db.commit()
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@asignaciones_router.get("", response_model=list[AsignacionResponse])
async def listar_asignaciones(
    user: RequiereAsignaciones,
    db: AsyncSession = Depends(get_db),
    usuario_id: uuid.UUID | None = Query(default=None),
    rol_id: uuid.UUID | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
) -> list[AsignacionResponse]:
    service = _build_service(user, db)
    return await service.listar_asignaciones(
        usuario_id=usuario_id,
        rol_id=rol_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )


@asignaciones_router.post("", response_model=AsignacionResponse, status_code=status.HTTP_201_CREATED)
async def crear_asignacion(payload: AsignacionCreate, user: RequiereAsignaciones, db: AsyncSession = Depends(get_db)) -> AsignacionResponse:
    service = _build_service(user, db)
    try:
        asignacion = await service.crear_asignacion(**payload.model_dump())
        await db.commit()
        await db.refresh(asignacion)
        return asignacion
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@asignaciones_router.get("/{asignacion_id}", response_model=AsignacionResponse)
async def obtener_asignacion(asignacion_id: uuid.UUID, user: RequiereAsignaciones, db: AsyncSession = Depends(get_db)) -> AsignacionResponse:
    service = _build_service(user, db)
    try:
        return await service.obtener_asignacion(asignacion_id)
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@asignaciones_router.patch("/{asignacion_id}", response_model=AsignacionResponse)
async def actualizar_asignacion(asignacion_id: uuid.UUID, payload: AsignacionUpdate, user: RequiereAsignaciones, db: AsyncSession = Depends(get_db)) -> AsignacionResponse:
    service = _build_service(user, db)
    try:
        asignacion = await service.actualizar_asignacion(asignacion_id, **payload.model_dump(exclude_unset=True))
        await db.commit()
        await db.refresh(asignacion)
        return asignacion
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)


@asignaciones_router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_asignacion(asignacion_id: uuid.UUID, user: RequiereAsignaciones, db: AsyncSession = Depends(get_db)) -> None:
    service = _build_service(user, db)
    try:
        await service.eliminar_asignacion(asignacion_id)
        await db.commit()
    except (ConflictError, NotFoundError) as exc:
        _handle_service_error(exc)
