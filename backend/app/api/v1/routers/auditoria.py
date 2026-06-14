from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.auditoria import (
    AccionPorDiaResponse,
    AuditLogResponse,
    EstadoComunicacionResponse,
    InteraccionDocenteResponse,
)
from app.services.auditoria_service import AuditoriaService


router = APIRouter(prefix="/api/auditoria", tags=["auditoria"])

RequiereVer = Annotated[AuthenticatedUser, require_permission("auditoria:ver")]


def _svc(user: AuthenticatedUser, db: AsyncSession) -> AuditoriaService:
    return AuditoriaService(session=db, tenant_id=user.tenant_id)


@router.get("/acciones-por-dia", response_model=list[AccionPorDiaResponse])
async def acciones_por_dia(
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    usuario_id: uuid.UUID | None = Query(default=None),
) -> list[AccionPorDiaResponse]:
    return await _svc(user, db).acciones_por_dia(
        roles=user.roles,
        user_auth_id=user.user_id,
        desde=desde,
        hasta=hasta,
        materia_id=materia_id,
        usuario_id=usuario_id,
    )


@router.get("/estado-comunicaciones", response_model=list[EstadoComunicacionResponse])
async def estado_comunicaciones(
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
) -> list[EstadoComunicacionResponse]:
    return await _svc(user, db).estado_comunicaciones(
        roles=user.roles,
        user_auth_id=user.user_id,
    )


@router.get("/interacciones-docente", response_model=list[InteraccionDocenteResponse])
async def interacciones_docente(
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    usuario_id: uuid.UUID | None = Query(default=None),
) -> list[InteraccionDocenteResponse]:
    return await _svc(user, db).interacciones_docente(
        roles=user.roles,
        user_auth_id=user.user_id,
        desde=desde,
        hasta=hasta,
        materia_id=materia_id,
        usuario_id=usuario_id,
    )


@router.get("/log", response_model=list[AuditLogResponse])
async def log(
    user: RequiereVer,
    db: AsyncSession = Depends(get_db),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    accion: str | None = Query(default=None),
    usuario_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AuditLogResponse]:
    return await _svc(user, db).log(
        roles=user.roles,
        user_auth_id=user.user_id,
        desde=desde,
        hasta=hasta,
        accion=accion,
        usuario_id=usuario_id,
        limit=limit,
    )
