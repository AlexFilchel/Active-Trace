from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import csv
import io
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.analisis.repositories import (
    ActividadAnalizadaRow,
    ActivePadronEntryRow,
    AnalisisQueryFilters,
    AnalisisRepository,
    AuthorizedScope,
    AuthorizedScopeAssignment,
    FinalizacionActividadRow,
    LatestCalificacionRow,
    UmbralVigenteRow,
)
from app.analisis.schemas import (
    AtrasadoItemResponse,
    AtrasadoMotivoResponse,
    AtrasadosResponse,
    MateriaResumenResponse,
    MonitorItemResponse,
    MonitorResponse,
    NotaFinalActividadResponse,
    NotaFinalItemResponse,
    NotasFinalesResponse,
    PaginationResponse,
    RankingItemResponse,
    RankingResponse,
)
from app.core.dependencies import AuthenticatedUser
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository

_DEFAULT_UMBRAL_PCT = Decimal("60")
_DEFAULT_VALORES_APROBATORIOS = ("Satisfactorio", "Supera lo esperado")
_GLOBAL_ROLES = {"COORDINADOR", "ADMIN"}


@dataclass(frozen=True, slots=True)
class AnalisisExportResult:
    filename: str
    content: bytes
    media_type: str = "text/csv; charset=utf-8"


@dataclass(slots=True)
class _StudentMetrics:
    entry: ActivePadronEntryRow
    aprobadas_count: int
    actividades_pendientes: int
    motivos: list[AtrasadoMotivoResponse]
    ultima_actividad_at: date | None
    actividades: list[NotaFinalActividadResponse]
    nota_final: Decimal | None
    tiene_nota_final: bool


class AnalisisService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = AnalisisRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=self.tenant_id)

    async def _resolve_scope(self, user: AuthenticatedUser) -> AuthorizedScope:
        if any(role in _GLOBAL_ROLES for role in user.roles):
            return AuthorizedScope(is_global=True)

        usuario = await self._usuario_repo.get_by_auth_user_id(user.user_id)
        if usuario is None:
            return AuthorizedScope(is_global=False, assignments=())

        assignments = await self._asignacion_repo.list(usuario_id=usuario.id, active_only=True)
        return AuthorizedScope(
            is_global=False,
            assignments=tuple(
                AuthorizedScopeAssignment(
                    materia_id=assignment.materia_id,
                    cohorte_id=assignment.cohorte_id,
                    comisiones=tuple(assignment.comisiones or []),
                )
                for assignment in assignments
            ),
        )

    async def _load_metrics(self, user: AuthenticatedUser, filters: AnalisisQueryFilters) -> tuple[list[_StudentMetrics], list[ActividadAnalizadaRow]]:
        scope = await self._resolve_scope(user)
        if not scope.is_global and not scope.assignments:
            return [], []

        entries = await self._repo.list_active_padron_entries(filters, scope)
        activities = await self._repo.list_actividades_analizadas(filters, scope)
        latest_rows = await self._repo.list_latest_calificaciones(filters, scope)
        umbrales = await self._repo.list_umbral_vigente(filters, scope)

        thresholds = {(row.actor_id, row.materia_id): row for row in umbrales}
        activities_by_materia: dict[uuid.UUID, list[ActividadAnalizadaRow]] = {}
        for activity in activities:
            activities_by_materia.setdefault(activity.materia_id, []).append(activity)

        latest_by_entry_activity = {(row.entrada_padron_id, row.actividad): row for row in latest_rows}

        metrics: list[_StudentMetrics] = []
        for entry in entries:
            materia_activities = activities_by_materia.get(entry.materia_id, [])
            motivos: list[AtrasadoMotivoResponse] = []
            aprobadas_count = 0
            ultima_actividad_at = None
            nota_items: list[NotaFinalActividadResponse] = []
            numeric_values: list[Decimal] = []

            for activity in materia_activities:
                row = latest_by_entry_activity.get((entry.entrada_padron_id, activity.actividad))
                if row is None:
                    motivos.append(AtrasadoMotivoResponse(tipo="actividad_faltante", actividad=activity.actividad))
                    continue

                nota_items.append(
                    NotaFinalActividadResponse(
                        actividad=activity.actividad,
                        nota_numerica=row.nota_numerica,
                        nota_textual=row.nota_textual,
                    )
                )
                ultima_fecha = row.created_at.date()
                if ultima_actividad_at is None or ultima_fecha > ultima_actividad_at:
                    ultima_actividad_at = ultima_fecha

                if row.nota_numerica is not None:
                    numeric_values.append(Decimal(str(row.nota_numerica)))

                if self._is_approved(row, thresholds):
                    aprobadas_count += 1
                else:
                    motivos.append(
                        AtrasadoMotivoResponse(
                            tipo="nota_bajo_umbral",
                            actividad=activity.actividad,
                            valor_observado=str(row.nota_numerica) if row.nota_numerica is not None else row.nota_textual,
                            umbral_aplicable=self._threshold_for(row, thresholds).umbral_pct,
                        )
                    )

            nota_final = None
            if numeric_values:
                nota_final = sum(numeric_values) / Decimal(len(numeric_values))

            metrics.append(
                _StudentMetrics(
                    entry=entry,
                    aprobadas_count=aprobadas_count,
                    actividades_pendientes=sum(1 for motivo in motivos if motivo.tipo == "actividad_faltante"),
                    motivos=motivos,
                    ultima_actividad_at=ultima_actividad_at,
                    actividades=nota_items,
                    nota_final=nota_final,
                    tiene_nota_final=nota_final is not None,
                )
            )

        return metrics, activities

    def _threshold_for(
        self,
        row: LatestCalificacionRow,
        thresholds: dict[tuple[uuid.UUID, uuid.UUID], UmbralVigenteRow],
    ) -> UmbralVigenteRow:
        return thresholds.get(
            (row.actor_id, row.materia_id),
            UmbralVigenteRow(
                actor_id=row.actor_id,
                materia_id=row.materia_id,
                umbral_pct=_DEFAULT_UMBRAL_PCT,
                valores_aprobatorios=_DEFAULT_VALORES_APROBATORIOS,
            ),
        )

    def _is_approved(
        self,
        row: LatestCalificacionRow,
        thresholds: dict[tuple[uuid.UUID, uuid.UUID], UmbralVigenteRow],
    ) -> bool:
        threshold = self._threshold_for(row, thresholds)
        if row.nota_numerica is not None:
            return Decimal(str(row.nota_numerica)) >= threshold.umbral_pct
        if row.nota_textual is not None:
            return row.nota_textual in threshold.valores_aprobatorios
        return False

    def _paginate[T](self, items: list[T], page: int, page_size: int) -> tuple[list[T], PaginationResponse]:
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], PaginationResponse(page=page, page_size=page_size, total_items=len(items))

    async def list_atrasados(self, user: AuthenticatedUser, **raw_filters) -> AtrasadosResponse:
        metrics, _ = await self._load_metrics(user, AnalisisQueryFilters(**raw_filters))
        items = [
            AtrasadoItemResponse(
                entrada_padron_id=metric.entry.entrada_padron_id,
                nombre=metric.entry.nombre,
                apellidos=metric.entry.apellidos,
                comision=metric.entry.comision,
                regional=metric.entry.regional,
                motivos=metric.motivos,
                actividades_pendientes=metric.actividades_pendientes,
                aprobadas_count=metric.aprobadas_count,
            )
            for metric in metrics
            if metric.motivos
        ]
        items.sort(key=lambda item: (-len(item.motivos), item.apellidos, item.nombre, str(item.entrada_padron_id)))
        return AtrasadosResponse(total_items=len(items), items=items)

    async def list_ranking(self, user: AuthenticatedUser, **raw_filters) -> RankingResponse:
        filters = AnalisisQueryFilters(**raw_filters)
        metrics, _ = await self._load_metrics(user, filters)
        items = [
            RankingItemResponse(
                entrada_padron_id=metric.entry.entrada_padron_id,
                nombre=metric.entry.nombre,
                apellidos=metric.entry.apellidos,
                comision=metric.entry.comision,
                aprobadas_count=metric.aprobadas_count,
            )
            for metric in metrics
            if metric.aprobadas_count >= 1
        ]
        items.sort(key=lambda item: (-item.aprobadas_count, item.apellidos, item.nombre, str(item.entrada_padron_id)))
        paged_items, pagination = self._paginate(items, filters.page, filters.page_size)
        return RankingResponse(pagination=pagination, items=paged_items)

    async def get_materia_resumen(self, user: AuthenticatedUser, **raw_filters) -> MateriaResumenResponse:
        metrics, activities = await self._load_metrics(user, AnalisisQueryFilters(**raw_filters))
        if not metrics:
            return MateriaResumenResponse(estado="sin_datos", alumnos_activos=0, actividades_analizadas=0, aprobaciones_total=0, alumnos_atrasados=0)
        if not activities:
            return MateriaResumenResponse(
                estado="sin_actividades",
                alumnos_activos=len(metrics),
                actividades_analizadas=0,
                aprobaciones_total=0,
                alumnos_atrasados=0,
            )
        return MateriaResumenResponse(
            estado="ok",
            alumnos_activos=len(metrics),
            actividades_analizadas=len(activities),
            aprobaciones_total=sum(metric.aprobadas_count for metric in metrics),
            alumnos_atrasados=sum(1 for metric in metrics if metric.motivos),
        )

    async def list_notas_finales(self, user: AuthenticatedUser, **raw_filters) -> NotasFinalesResponse:
        metrics, _ = await self._load_metrics(user, AnalisisQueryFilters(**raw_filters))
        items = [
            NotaFinalItemResponse(
                entrada_padron_id=metric.entry.entrada_padron_id,
                nombre=metric.entry.nombre,
                apellidos=metric.entry.apellidos,
                comision=metric.entry.comision,
                nota_final=metric.nota_final,
                tiene_nota_final=metric.tiene_nota_final,
                actividades=metric.actividades,
            )
            for metric in sorted(metrics, key=lambda metric: (metric.entry.apellidos, metric.entry.nombre, str(metric.entry.entrada_padron_id)))
        ]
        return NotasFinalesResponse(items=items)

    async def list_monitor(self, user: AuthenticatedUser, **raw_filters) -> MonitorResponse:
        filters = AnalisisQueryFilters(**raw_filters)
        metrics, _ = await self._load_metrics(user, filters)

        filtered_metrics = metrics
        if filters.estado == "atrasado":
            filtered_metrics = [metric for metric in filtered_metrics if metric.motivos]
        elif filters.estado == "al_dia":
            filtered_metrics = [metric for metric in filtered_metrics if not metric.motivos]

        if filters.fecha_desde or filters.fecha_hasta:
            filtered_metrics = [
                metric
                for metric in filtered_metrics
                if metric.ultima_actividad_at is not None
                and (filters.fecha_desde is None or metric.ultima_actividad_at >= filters.fecha_desde)
                and (filters.fecha_hasta is None or metric.ultima_actividad_at <= filters.fecha_hasta)
            ]

        if filters.criterio == "aprobadas_desc":
            filtered_metrics.sort(key=lambda metric: (-metric.aprobadas_count, metric.entry.apellidos, metric.entry.nombre, str(metric.entry.entrada_padron_id)))
        elif filters.criterio == "nombre_asc":
            filtered_metrics.sort(key=lambda metric: (metric.entry.apellidos, metric.entry.nombre, str(metric.entry.entrada_padron_id)))
        else:
            filtered_metrics.sort(key=lambda metric: (-len(metric.motivos), metric.entry.apellidos, metric.entry.nombre, str(metric.entry.entrada_padron_id)))

        items = [
            MonitorItemResponse(
                entrada_padron_id=metric.entry.entrada_padron_id,
                nombre=metric.entry.nombre,
                apellidos=metric.entry.apellidos,
                comision=metric.entry.comision,
                regional=metric.entry.regional,
                aprobadas_count=metric.aprobadas_count,
                actividades_pendientes=metric.actividades_pendientes,
                estado="atrasado" if metric.motivos else "al_dia",
                ultima_actividad_at=metric.ultima_actividad_at,
            )
            for metric in filtered_metrics
        ]
        paged_items, pagination = self._paginate(items, filters.page, filters.page_size)
        return MonitorResponse(pagination=pagination, items=paged_items)

    async def export_tps_sin_corregir(self, user: AuthenticatedUser, **raw_filters) -> AnalisisExportResult:
        filters = AnalisisQueryFilters(**raw_filters)
        scope = await self._resolve_scope(user)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["alumno", "apellido", "materia", "actividad", "comision", "regional", "ultima_finalizacion_at"])

        if not scope.is_global and not scope.assignments:
            return AnalisisExportResult(filename="tps-sin-corregir.csv", content=buffer.getvalue().encode("utf-8"))

        entries = await self._repo.list_active_padron_entries(filters, scope)
        latest_rows = await self._repo.list_latest_calificaciones(filters, scope)
        finalizaciones = await self._repo.list_finalizaciones_actividades(filters, scope)
        entries_by_id = {entry.entrada_padron_id: entry for entry in entries}
        actividades_calificadas = {(row.entrada_padron_id, row.actividad) for row in latest_rows}

        exportables: list[tuple[ActivePadronEntryRow, FinalizacionActividadRow]] = []
        for finalizacion in finalizaciones:
            entry = entries_by_id.get(finalizacion.entrada_padron_id)
            if entry is None:
                continue
            if not finalizacion.finalizado or not finalizacion.es_textual:
                continue
            if (finalizacion.entrada_padron_id, finalizacion.actividad) in actividades_calificadas:
                continue
            exportables.append((entry, finalizacion))

        for entry, finalizacion in sorted(
            exportables,
            key=lambda item: (item[0].apellidos, item[0].nombre, item[1].actividad, str(item[0].entrada_padron_id)),
        ):
            writer.writerow([
                entry.nombre,
                entry.apellidos,
                entry.materia_nombre,
                finalizacion.actividad,
                entry.comision or "",
                entry.regional or "",
                finalizacion.updated_at.date().isoformat(),
            ])
        return AnalisisExportResult(filename="tps-sin-corregir.csv", content=buffer.getvalue().encode("utf-8"))
