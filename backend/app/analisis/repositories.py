from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import Select, and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion, FinalizacionActividad, UmbralMateria
from app.models.estructura import Cohorte, Materia
from app.models.padron import EntradaPadron, VersionPadron
from app.models.usuarios import Asignacion
from app.repositories.tenant_scoped import TenantScopedRepository


@dataclass(frozen=True, slots=True)
class AuthorizedScopeAssignment:
    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comisiones: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AuthorizedScope:
    is_global: bool
    assignments: tuple[AuthorizedScopeAssignment, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalisisQueryFilters:
    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comision: str | None = None
    regional: str | None = None
    search: str | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    estado: str | None = None
    criterio: str | None = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True, slots=True)
class ActivePadronEntryRow:
    tenant_id: uuid.UUID
    entrada_padron_id: uuid.UUID
    version_id: uuid.UUID
    materia_id: uuid.UUID
    materia_nombre: str
    cohorte_id: uuid.UUID
    cohorte_nombre: str
    usuario_id: uuid.UUID | None
    nombre: str
    apellidos: str
    comision: str | None
    regional: str | None


@dataclass(frozen=True, slots=True)
class ActividadAnalizadaRow:
    materia_id: uuid.UUID
    actividad: str
    es_textual: bool


@dataclass(frozen=True, slots=True)
class LatestCalificacionRow:
    tenant_id: uuid.UUID
    entrada_padron_id: uuid.UUID
    materia_id: uuid.UUID
    actor_id: uuid.UUID
    actividad: str
    nota_numerica: Decimal | None
    nota_textual: str | None
    aprobado: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FinalizacionActividadRow:
    entrada_padron_id: uuid.UUID
    actividad: str
    es_textual: bool
    finalizado: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UmbralVigenteRow:
    actor_id: uuid.UUID
    materia_id: uuid.UUID
    umbral_pct: Decimal
    valores_aprobatorios: tuple[str, ...]


class AnalisisRepository(TenantScopedRepository[EntradaPadron]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=EntradaPadron, tenant_id=tenant_id)

    def _is_fail_closed_scope(self, scope: AuthorizedScope) -> bool:
        return not scope.is_global and not scope.assignments

    def _scope_condition(self, scope: AuthorizedScope) -> object:
        if scope.is_global:
            return literal(True)
        if not scope.assignments:
            return literal(False)

        clauses = []
        for assignment in scope.assignments:
            clause = literal(True)
            if assignment.materia_id is not None:
                clause = and_(clause, VersionPadron.materia_id == assignment.materia_id)
            if assignment.cohorte_id is not None:
                clause = and_(clause, VersionPadron.cohorte_id == assignment.cohorte_id)
            if assignment.comisiones:
                clause = and_(clause, EntradaPadron.comision.in_(assignment.comisiones))
            clauses.append(clause)
        return or_(*clauses) if clauses else literal(False)

    def _apply_entry_filters(self, stmt: Select, filters: AnalisisQueryFilters) -> Select:
        if filters.materia_id is not None:
            stmt = stmt.where(VersionPadron.materia_id == filters.materia_id)
        if filters.cohorte_id is not None:
            stmt = stmt.where(VersionPadron.cohorte_id == filters.cohorte_id)
        if filters.comision:
            stmt = stmt.where(EntradaPadron.comision == filters.comision)
        if filters.regional:
            stmt = stmt.where(EntradaPadron.regional == filters.regional)
        if filters.search:
            search = f"%{filters.search.strip()}%"
            stmt = stmt.where(
                or_(
                    EntradaPadron.nombre.ilike(search),
                    EntradaPadron.apellidos.ilike(search),
                )
            )
        return stmt

    def _base_entry_stmt(self, filters: AnalisisQueryFilters, scope: AuthorizedScope) -> Select:
        stmt = (
            select(EntradaPadron, VersionPadron, Materia, Cohorte)
            .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
            .join(Materia, Materia.id == VersionPadron.materia_id)
            .join(Cohorte, Cohorte.id == VersionPadron.cohorte_id)
            .where(EntradaPadron.tenant_id == self.context.tenant_id)
            .where(VersionPadron.tenant_id == self.context.tenant_id)
            .where(Materia.tenant_id == self.context.tenant_id)
            .where(Cohorte.tenant_id == self.context.tenant_id)
            .where(EntradaPadron.deleted_at.is_(None))
            .where(VersionPadron.deleted_at.is_(None))
            .where(Materia.deleted_at.is_(None))
            .where(Cohorte.deleted_at.is_(None))
            .where(VersionPadron.activa.is_(True))
            .where(self._scope_condition(scope))
        )
        return self._apply_entry_filters(stmt, filters)

    async def list_active_padron_entries(
        self,
        filters: AnalisisQueryFilters,
        scope: AuthorizedScope,
    ) -> list[ActivePadronEntryRow]:
        stmt = self._base_entry_stmt(filters, scope).order_by(EntradaPadron.apellidos, EntradaPadron.nombre, EntradaPadron.id)
        rows = (await self.session.execute(stmt)).all()
        return [
            ActivePadronEntryRow(
                tenant_id=entry.tenant_id,
                entrada_padron_id=entry.id,
                version_id=version.id,
                materia_id=version.materia_id,
                materia_nombre=materia.nombre,
                cohorte_id=version.cohorte_id,
                cohorte_nombre=cohorte.nombre,
                usuario_id=entry.usuario_id,
                nombre=entry.nombre,
                apellidos=entry.apellidos,
                comision=entry.comision,
                regional=entry.regional,
            )
            for entry, version, materia, cohorte in rows
        ]

    async def list_actividades_analizadas(
        self,
        filters: AnalisisQueryFilters,
        scope: AuthorizedScope,
    ) -> list[ActividadAnalizadaRow]:
        stmt = (
            select(
                VersionPadron.materia_id,
                Calificacion.actividad,
                case((Calificacion.actividad.endswith("(Real)"), literal(False)), else_=literal(True)).label("es_textual"),
            )
            .join(EntradaPadron, EntradaPadron.id == Calificacion.entrada_padron_id)
            .join(VersionPadron, VersionPadron.id == EntradaPadron.version_id)
            .where(Calificacion.tenant_id == self.context.tenant_id)
            .where(EntradaPadron.tenant_id == self.context.tenant_id)
            .where(VersionPadron.tenant_id == self.context.tenant_id)
            .where(Calificacion.deleted_at.is_(None))
            .where(EntradaPadron.deleted_at.is_(None))
            .where(VersionPadron.deleted_at.is_(None))
            .where(VersionPadron.activa.is_(True))
            .where(self._scope_condition(scope))
        )
        if filters.materia_id is not None:
            stmt = stmt.where(VersionPadron.materia_id == filters.materia_id)
        if filters.cohorte_id is not None:
            stmt = stmt.where(VersionPadron.cohorte_id == filters.cohorte_id)
        stmt = stmt.distinct().order_by(VersionPadron.materia_id, Calificacion.actividad)
        rows = (await self.session.execute(stmt)).all()
        return [ActividadAnalizadaRow(materia_id=materia_id, actividad=actividad, es_textual=es_textual) for materia_id, actividad, es_textual in rows]

    async def list_latest_calificaciones(
        self,
        filters: AnalisisQueryFilters,
        scope: AuthorizedScope,
    ) -> list[LatestCalificacionRow]:
        latest_subquery = (
            select(
                Calificacion.tenant_id.label("tenant_id"),
                Calificacion.entrada_padron_id.label("entrada_padron_id"),
                VersionPadron.materia_id.label("materia_id"),
                Calificacion.actor_id.label("actor_id"),
                Calificacion.actividad.label("actividad"),
                Calificacion.nota_numerica.label("nota_numerica"),
                Calificacion.nota_textual.label("nota_textual"),
                Calificacion.aprobado.label("aprobado"),
                Calificacion.created_at.label("created_at"),
                func.row_number()
                .over(
                    partition_by=(Calificacion.entrada_padron_id, Calificacion.actividad),
                    order_by=(Calificacion.updated_at.desc(), Calificacion.created_at.desc(), Calificacion.id.desc()),
                )
                .label("rn"),
            )
            .join(EntradaPadron, EntradaPadron.id == Calificacion.entrada_padron_id)
            .join(VersionPadron, VersionPadron.id == EntradaPadron.version_id)
            .where(Calificacion.tenant_id == self.context.tenant_id)
            .where(EntradaPadron.tenant_id == self.context.tenant_id)
            .where(VersionPadron.tenant_id == self.context.tenant_id)
            .where(Calificacion.deleted_at.is_(None))
            .where(EntradaPadron.deleted_at.is_(None))
            .where(VersionPadron.deleted_at.is_(None))
            .where(VersionPadron.activa.is_(True))
            .where(self._scope_condition(scope))
        )
        latest_subquery = self._apply_entry_filters(latest_subquery, filters).subquery()
        stmt = (
            select(latest_subquery)
            .where(latest_subquery.c.rn == 1)
            .order_by(latest_subquery.c.actividad, latest_subquery.c.entrada_padron_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            LatestCalificacionRow(
                tenant_id=row.tenant_id,
                entrada_padron_id=row.entrada_padron_id,
                materia_id=row.materia_id,
                actor_id=row.actor_id,
                actividad=row.actividad,
                nota_numerica=row.nota_numerica,
                nota_textual=row.nota_textual,
                aprobado=row.aprobado,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def list_finalizaciones_actividades(
        self,
        filters: AnalisisQueryFilters,
        scope: AuthorizedScope,
    ) -> list[FinalizacionActividadRow]:
        stmt = (
            select(
                FinalizacionActividad.entrada_padron_id,
                FinalizacionActividad.actividad,
                FinalizacionActividad.es_textual,
                FinalizacionActividad.finalizado,
                FinalizacionActividad.updated_at,
            )
            .join(EntradaPadron, EntradaPadron.id == FinalizacionActividad.entrada_padron_id)
            .join(VersionPadron, VersionPadron.id == EntradaPadron.version_id)
            .where(FinalizacionActividad.tenant_id == self.context.tenant_id)
            .where(EntradaPadron.tenant_id == self.context.tenant_id)
            .where(VersionPadron.tenant_id == self.context.tenant_id)
            .where(FinalizacionActividad.deleted_at.is_(None))
            .where(EntradaPadron.deleted_at.is_(None))
            .where(VersionPadron.deleted_at.is_(None))
            .where(VersionPadron.activa.is_(True))
            .where(self._scope_condition(scope))
        )
        stmt = self._apply_entry_filters(stmt, filters).order_by(
            FinalizacionActividad.actividad,
            FinalizacionActividad.entrada_padron_id,
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            FinalizacionActividadRow(
                entrada_padron_id=entrada_padron_id,
                actividad=actividad,
                es_textual=es_textual,
                finalizado=finalizado,
                updated_at=updated_at,
            )
            for entrada_padron_id, actividad, es_textual, finalizado, updated_at in rows
        ]

    async def list_umbral_vigente(
        self,
        filters: AnalisisQueryFilters,
        scope: AuthorizedScope,
    ) -> list[UmbralVigenteRow]:
        if self._is_fail_closed_scope(scope):
            return []

        stmt = (
            select(Asignacion.usuario_id, UmbralMateria.materia_id, UmbralMateria.umbral_pct, UmbralMateria.valores_aprobatorios)
            .join(Asignacion, Asignacion.id == UmbralMateria.asignacion_id)
            .where(UmbralMateria.tenant_id == self.context.tenant_id)
            .where(Asignacion.tenant_id == self.context.tenant_id)
            .where(UmbralMateria.deleted_at.is_(None))
            .where(Asignacion.deleted_at.is_(None))
        )
        if filters.materia_id is not None:
            stmt = stmt.where(UmbralMateria.materia_id == filters.materia_id)
        if not scope.is_global and scope.assignments:
            materia_ids = tuple({assignment.materia_id for assignment in scope.assignments if assignment.materia_id is not None})
            cohorte_ids = tuple({assignment.cohorte_id for assignment in scope.assignments if assignment.cohorte_id is not None})
            if materia_ids:
                stmt = stmt.where(UmbralMateria.materia_id.in_(materia_ids))
            if cohorte_ids:
                stmt = stmt.where(or_(Asignacion.cohorte_id.is_(None), Asignacion.cohorte_id.in_(cohorte_ids)))
        rows = (await self.session.execute(stmt)).all()
        return [
            UmbralVigenteRow(
                actor_id=actor_id,
                materia_id=materia_id,
                umbral_pct=umbral_pct,
                valores_aprobatorios=tuple(valores_aprobatorios),
            )
            for actor_id, materia_id, umbral_pct, valores_aprobatorios in rows
        ]
