from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission
from app.schemas.coloquios import (
    AgendaDiaResponse,
    CancelarReservaRequest,
    ConvocatoriaResponse,
    CrearConvocatoriaRequest,
    EditarConvocatoriaRequest,
    ImportarCandidatosRequest,
    MetricasResponse,
    RegistrarResultadoRequest,
    ReservaResponse,
    ReservarTurnoRequest,
    ResultadoResponse,
)
from app.services.coloquio_service import (
    ColoquioNotFoundError,
    ColoquioService,
    ConvocatoriaCerradaError,
    NoCandidatoError,
    ReservaDuplicadaError,
    ReservaNoEncontradaError,
    SinCupoError,
)


router = APIRouter(prefix="/api/coloquios", tags=["coloquios"])

RequiereGestionar = Annotated[AuthenticatedUser, require_permission("coloquios:gestionar")]
RequiereReservar = Annotated[AuthenticatedUser, require_permission("evaluacion:reservar_instancia")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> ColoquioService:
    return ColoquioService(session=db, tenant_id=user.tenant_id)


def _ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


# ---------------------------------------------------------------------------
# Gestión (COORDINADOR / ADMIN)
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConvocatoriaResponse)
async def crear_convocatoria(
    payload: CrearConvocatoriaRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ConvocatoriaResponse:
    try:
        result = await _service(user, db).crear_convocatoria(
            actor_id=user.user_id,
            payload=payload,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except ColoquioNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("", response_model=list[ConvocatoriaResponse])
async def listar_convocatorias(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> list[ConvocatoriaResponse]:
    return await _service(user, db).listar_convocatorias()


@router.get("/metricas", response_model=MetricasResponse)
async def metricas(
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> MetricasResponse:
    return await _service(user, db).metricas()


@router.patch("/{evaluacion_id}", response_model=ConvocatoriaResponse)
async def editar_convocatoria(
    evaluacion_id: uuid.UUID,
    payload: EditarConvocatoriaRequest,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> ConvocatoriaResponse:
    try:
        result = await _service(user, db).editar_convocatoria(evaluacion_id, payload)
        await db.commit()
        return result
    except ColoquioNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{evaluacion_id}/candidatos", status_code=status.HTTP_200_OK)
async def importar_candidatos(
    evaluacion_id: uuid.UUID,
    payload: ImportarCandidatosRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        added = await _service(user, db).importar_candidatos(
            actor_id=user.user_id,
            evaluacion_id=evaluacion_id,
            alumno_ids=payload.alumno_ids,
            ip=_ip(request),
        )
        await db.commit()
        return {"candidatos_agregados": added}
    except ColoquioNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{evaluacion_id}/agenda", response_model=list[AgendaDiaResponse])
async def agenda(
    evaluacion_id: uuid.UUID,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> list[AgendaDiaResponse]:
    try:
        return await _service(user, db).agenda(evaluacion_id)
    except ColoquioNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{evaluacion_id}/resultados", status_code=status.HTTP_201_CREATED, response_model=ResultadoResponse)
async def registrar_resultado(
    evaluacion_id: uuid.UUID,
    payload: RegistrarResultadoRequest,
    user: RequiereGestionar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ResultadoResponse:
    try:
        result = await _service(user, db).registrar_resultado(
            actor_id=user.user_id,
            evaluacion_id=evaluacion_id,
            alumno_id=payload.alumno_id,
            nota_final=payload.nota_final,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except ColoquioNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{evaluacion_id}/resultados", response_model=list[ResultadoResponse])
async def listar_resultados(
    evaluacion_id: uuid.UUID,
    user: RequiereGestionar,
    db: AsyncSession = Depends(get_db),
) -> list[ResultadoResponse]:
    try:
        return await _service(user, db).listar_resultados(evaluacion_id)
    except ColoquioNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# Reservas (ALUMNO)
# ---------------------------------------------------------------------------

@router.post("/{evaluacion_id}/reservas", status_code=status.HTTP_201_CREATED, response_model=ReservaResponse)
async def reservar(
    evaluacion_id: uuid.UUID,
    payload: ReservarTurnoRequest,
    user: RequiereReservar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ReservaResponse:
    try:
        result = await _service(user, db).reservar(
            actor_id_alumno=user.user_id,
            evaluacion_id=evaluacion_id,
            dia_evaluacion_id=payload.dia_evaluacion_id,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except (ColoquioNotFoundError, ReservaDuplicadaError, SinCupoError, ConvocatoriaCerradaError) as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except NoCandidatoError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.patch("/reservas/{reserva_id}", response_model=ReservaResponse)
async def cancelar_reserva(
    reserva_id: uuid.UUID,
    payload: CancelarReservaRequest,
    user: RequiereReservar,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ReservaResponse:
    try:
        result = await _service(user, db).cancelar_reserva(
            actor_id_alumno=user.user_id,
            reserva_id=reserva_id,
            ip=_ip(request),
        )
        await db.commit()
        return result
    except ReservaNoEncontradaError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
