from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.guardias import GuardiaResponse, RegistrarGuardiaRequest
from app.services.guardia_service import GuardiaNotFoundError, GuardiaService


router = APIRouter(prefix="/api/guardias", tags=["guardias"])
RequiereRegistrar = Annotated[AuthenticatedUser, require_permission("guardias:registrar")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> GuardiaService:
    return GuardiaService(session=db, tenant_id=user.tenant_id)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GuardiaResponse)
async def registrar_guardia(
    payload: RegistrarGuardiaRequest,
    user: RequiereRegistrar,
    db: AsyncSession = Depends(get_db),
) -> GuardiaResponse:
    try:
        guardia = await _service(user, db).registrar(
            actor_id=user.user_id,
            payload=payload,
        )
        await db.commit()
        return GuardiaResponse.model_validate(guardia)
    except GuardiaNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("", response_model=list[GuardiaResponse])
async def listar_guardias(
    user: RequiereRegistrar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = None,
    carrera_id: uuid.UUID | None = None,
    cohorte_id: uuid.UUID | None = None,
    estado: str | None = None,
) -> list[GuardiaResponse]:
    guardias = await _service(user, db).listar(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        estado=estado,
    )
    return [GuardiaResponse.model_validate(g) for g in guardias]


@router.get("/exportar")
async def exportar_guardias(
    user: RequiereRegistrar,
    db: AsyncSession = Depends(get_db),
    materia_id: uuid.UUID | None = None,
    carrera_id: uuid.UUID | None = None,
    cohorte_id: uuid.UUID | None = None,
    estado: str | None = None,
) -> StreamingResponse:
    csv_content = await _service(user, db).exportar(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        estado=estado,
    )

    def _iter():
        yield csv_content.encode("utf-8")

    return StreamingResponse(
        _iter(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=guardias.csv"},
    )
