from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.analisis.schemas import AtrasadosResponse, BaseAnalisisQuery, MateriaResumenResponse, MonitorQuery, MonitorResponse, NotasFinalesResponse, RankingQuery, RankingResponse
from app.analisis.services import AnalisisService
from app.core.dependencies import AuthenticatedUser, get_db
from app.core.permissions import require_permission

router = APIRouter(prefix="/api/analisis", tags=["analisis"])

RequiereAnalisis = Annotated[AuthenticatedUser, require_permission("atrasados:ver")]


def _service(user: AuthenticatedUser, db: AsyncSession) -> AnalisisService:
    return AnalisisService(session=db, tenant_id=user.tenant_id)


@router.get("/atrasados", response_model=AtrasadosResponse)
async def get_atrasados(
    filtros: Annotated[BaseAnalisisQuery, Query()],
    user: RequiereAnalisis = None,
    db: AsyncSession = Depends(get_db),
) -> AtrasadosResponse:
    return await _service(user, db).list_atrasados(user, **filtros.model_dump())


@router.get("/ranking-aprobadas", response_model=RankingResponse)
async def get_ranking(
    filtros: Annotated[RankingQuery, Query()],
    user: RequiereAnalisis = None,
    db: AsyncSession = Depends(get_db),
) -> RankingResponse:
    return await _service(user, db).list_ranking(user, **filtros.model_dump())


@router.get("/materia/resumen", response_model=MateriaResumenResponse)
async def get_resumen_materia(
    filtros: Annotated[BaseAnalisisQuery, Query()],
    user: RequiereAnalisis = None,
    db: AsyncSession = Depends(get_db),
) -> MateriaResumenResponse:
    return await _service(user, db).get_materia_resumen(user, **filtros.model_dump())


@router.get("/notas-finales", response_model=NotasFinalesResponse)
async def get_notas_finales(
    filtros: Annotated[BaseAnalisisQuery, Query()],
    user: RequiereAnalisis = None,
    db: AsyncSession = Depends(get_db),
) -> NotasFinalesResponse:
    return await _service(user, db).list_notas_finales(user, **filtros.model_dump())


@router.get("/monitor", response_model=MonitorResponse)
async def get_monitor(
    filtros: Annotated[MonitorQuery, Query()],
    user: RequiereAnalisis = None,
    db: AsyncSession = Depends(get_db),
) -> MonitorResponse:
    return await _service(user, db).list_monitor(user, **filtros.model_dump())


@router.get("/tps-sin-corregir/export")
async def export_tps_sin_corregir(
    filtros: Annotated[BaseAnalisisQuery, Query()],
    user: RequiereAnalisis = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    export = await _service(user, db).export_tps_sin_corregir(user, **filtros.model_dump())
    return Response(
        content=export.content,
        media_type=export.media_type,
        headers={"Content-Disposition": f'attachment; filename="{export.filename}"'},
    )
