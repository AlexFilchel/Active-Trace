from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.models.usuarios import Usuario
from app.schemas.mensajeria import (
    CrearHiloRequest,
    HiloMensajeResponse,
    MensajeInternoResponse,
    ResponderHiloRequest,
)
from app.services.mensajeria_service import MensajeriaService

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

Autenticado = Annotated[AuthenticatedUser, Depends(get_current_user)]


def _svc(user: AuthenticatedUser, db: AsyncSession) -> MensajeriaService:
    return MensajeriaService(session=db, tenant_id=user.tenant_id)


async def _resolve_usuario_id(user: AuthenticatedUser, db: AsyncSession) -> uuid.UUID:
    """JWT user_id is auth_user.id; resolve to usuario.id for domain operations."""
    stmt = (
        select(Usuario.id)
        .where(Usuario.tenant_id == user.tenant_id)
        .where(Usuario.auth_user_id == user.user_id)
        .where(Usuario.deleted_at.is_(None))
    )
    usuario_id = await db.scalar(stmt)
    if usuario_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return usuario_id


@router.post("/hilos", response_model=HiloMensajeResponse, status_code=201)
async def crear_hilo(
    payload: CrearHiloRequest,
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
) -> HiloMensajeResponse:
    remitente_id = await _resolve_usuario_id(user, db)
    return await _svc(user, db).crear_hilo(
        remitente_id=remitente_id,
        destinatario_id=payload.destinatario_id,
        asunto=payload.asunto,
        cuerpo=payload.cuerpo,
    )


@router.get("/hilos", response_model=list[HiloMensajeResponse])
async def listar_hilos(
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
) -> list[HiloMensajeResponse]:
    usuario_id = await _resolve_usuario_id(user, db)
    return await _svc(user, db).listar_hilos(usuario_id)


@router.get("/hilos/{hilo_id}/mensajes", response_model=list[MensajeInternoResponse])
async def listar_mensajes(
    hilo_id: uuid.UUID,
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
) -> list[MensajeInternoResponse]:
    usuario_id = await _resolve_usuario_id(user, db)
    return await _svc(user, db).listar_mensajes(hilo_id, usuario_id)


@router.post("/hilos/{hilo_id}/mensajes", response_model=MensajeInternoResponse, status_code=201)
async def responder_hilo(
    hilo_id: uuid.UUID,
    payload: ResponderHiloRequest,
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
) -> MensajeInternoResponse:
    remitente_id = await _resolve_usuario_id(user, db)
    return await _svc(user, db).responder(
        hilo_id=hilo_id,
        remitente_id=remitente_id,
        destinatario_id=payload.destinatario_id,
        cuerpo=payload.cuerpo,
    )
