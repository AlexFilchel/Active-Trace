from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.core.security import decrypt_value, encrypt_value
from app.models.usuarios import Usuario
from app.schemas.perfil import PerfilResponse, PerfilUpdateRequest

router = APIRouter(prefix="/api/perfil", tags=["perfil"])

Autenticado = Annotated[AuthenticatedUser, Depends(get_current_user)]


def _decrypt_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return decrypt_value(value)


def _build_response(u: Usuario) -> PerfilResponse:
    return PerfilResponse(
        id=u.id,
        auth_user_id=u.auth_user_id,
        nombre=u.nombre,
        apellidos=u.apellidos,
        email=_decrypt_optional(u.email_encrypted),
        dni=_decrypt_optional(u.dni_encrypted),
        cuil=_decrypt_optional(u.cuil_encrypted),
        cbu=_decrypt_optional(u.cbu_encrypted),
        alias_cbu=_decrypt_optional(u.alias_cbu_encrypted),
        banco=u.banco,
        regional=u.regional,
        legajo=u.legajo,
        legajo_profesional=u.legajo_profesional,
        facturador=u.facturador,
        estado=u.estado,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


async def _get_usuario(user: AuthenticatedUser, db: AsyncSession) -> Usuario:
    stmt = (
        select(Usuario)
        .where(Usuario.tenant_id == user.tenant_id)
        .where(Usuario.auth_user_id == user.user_id)
        .where(Usuario.deleted_at.is_(None))
    )
    usuario = await db.scalar(stmt)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado.")
    return usuario


@router.get("", response_model=PerfilResponse)
async def get_perfil(
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
) -> PerfilResponse:
    usuario = await _get_usuario(user, db)
    return _build_response(usuario)


@router.patch("", response_model=PerfilResponse)
async def update_perfil(
    payload: PerfilUpdateRequest,
    user: Autenticado,
    db: AsyncSession = Depends(get_db),
) -> PerfilResponse:
    usuario = await _get_usuario(user, db)

    if payload.nombre is not None:
        usuario.nombre = payload.nombre
    if payload.apellidos is not None:
        usuario.apellidos = payload.apellidos
    if payload.banco is not None:
        usuario.banco = payload.banco
    if payload.cbu is not None:
        usuario.cbu_encrypted = encrypt_value(payload.cbu)
    if payload.alias_cbu is not None:
        usuario.alias_cbu_encrypted = encrypt_value(payload.alias_cbu)
    if payload.regional is not None:
        usuario.regional = payload.regional
    if payload.legajo_profesional is not None:
        usuario.legajo_profesional = payload.legajo_profesional
    if payload.facturador is not None:
        usuario.facturador = payload.facturador

    await db.commit()
    await db.refresh(usuario)
    return _build_response(usuario)
