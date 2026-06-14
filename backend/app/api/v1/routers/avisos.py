from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.avisos import (
    AckResponse,
    AvisoGestionResponse,
    AvisoResponse,
    CrearAvisoRequest,
    EditarAvisoRequest,
    MetricasAvisoResponse,
)
from app.services.aviso_service import (
    AvisoAckInvalidoError,
    AvisoNotFoundError,
    AvisoService,
)


router = APIRouter(prefix="/api/avisos", tags=["avisos"])

RequierePublicar = Annotated[AuthenticatedUser, require_permission("avisos:publicar")]
Autenticado = Annotated[AuthenticatedUser, Depends(get_current_user)]


def _service(user: AuthenticatedUser, db: AsyncSession) -> AvisoService:
    return AvisoService(session=db, tenant_id=user.tenant_id)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# Gestión (COORDINADOR / ADMIN) — /gestion MUST come before /{id}
# ---------------------------------------------------------------------------

@router.get("/gestion", response_model=list[AvisoGestionResponse])
async def listar_gestion(
    user: RequierePublicar,
    db: AsyncSession = Depends(get_db),
) -> list[AvisoGestionResponse]:
    return await _service(user, db).listar_gestion()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AvisoResponse)
async def crear_aviso(
    payload: CrearAvisoRequest,
    user: RequierePublicar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AvisoResponse:
    try:
        result = await _service(user, db).crear_aviso(
            actor_id=user.user_id,
            payload=payload,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except (AvisoNotFoundError, AvisoAckInvalidoError) as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# Usuario autenticado
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AvisoResponse])
async def listar_mis_avisos(
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
    incluir_acusados: bool = Query(default=False),
) -> list[AvisoResponse]:
    try:
        return await _service(user, db).listar_mis_avisos(
            auth_user_id=user.user_id,
            roles=user.roles,
            incluir_acusados=incluir_acusados,
        )
    except AvisoNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.patch("/{aviso_id}", response_model=AvisoResponse)
async def editar_aviso(
    aviso_id: uuid.UUID,
    payload: EditarAvisoRequest,
    user: RequierePublicar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AvisoResponse:
    try:
        result = await _service(user, db).editar_aviso(
            actor_id=user.user_id,
            aviso_id=aviso_id,
            payload=payload,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except AvisoNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{aviso_id}/ack", response_model=AckResponse)
async def ack_aviso(
    aviso_id: uuid.UUID,
    user: Autenticado,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AckResponse:
    try:
        response, created = await _service(user, db).ack(
            auth_user_id=user.user_id,
            aviso_id=aviso_id,
            ip=_ip(request),
        )
        await db.commit()
        from fastapi.responses import JSONResponse

        content = response.model_dump(mode="json")
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return JSONResponse(content=content, status_code=status_code)
    except AvisoNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except AvisoAckInvalidoError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{aviso_id}/metricas", response_model=MetricasAvisoResponse)
async def metricas_aviso(
    aviso_id: uuid.UUID,
    user: RequierePublicar,
    db: AsyncSession = Depends(get_db),
) -> MetricasAvisoResponse:
    try:
        return await _service(user, db).metricas(aviso_id)
    except AvisoNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
