from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluaciones import (
    CandidatoEvaluacion,
    DiaEvaluacion,
    Evaluacion,
    ReservaEvaluacion,
    ResultadoEvaluacion,
)
from app.repositories.tenant_scoped import TenantScopedRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvaluacionRepository(TenantScopedRepository[Evaluacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Evaluacion, tenant_id=tenant_id)

    # create, get, list, update inherited from TenantScopedRepository


class DiaEvaluacionRepository(TenantScopedRepository[DiaEvaluacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=DiaEvaluacion, tenant_id=tenant_id)

    async def bulk_create(self, dias: list[DiaEvaluacion]) -> list[DiaEvaluacion]:
        """Insert multiple DiaEvaluacion in a single flush."""
        for dia in dias:
            self.session.add(dia)
        await self.session.flush()
        return dias

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> list[DiaEvaluacion]:
        stmt = (
            self._base_query()
            .where(DiaEvaluacion.evaluacion_id == evaluacion_id)
            .order_by(DiaEvaluacion.fecha.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_for_update(self, dia_id: uuid.UUID) -> DiaEvaluacion | None:
        """Fetch a DiaEvaluacion with a row-level lock (SELECT ... FOR UPDATE)."""
        stmt = (
            self._base_query()
            .where(DiaEvaluacion.id == dia_id)
            .with_for_update()
        )
        return await self.session.scalar(stmt)


class CandidatoEvaluacionRepository(TenantScopedRepository[CandidatoEvaluacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=CandidatoEvaluacion, tenant_id=tenant_id)

    async def upsert_many(self, evaluacion_id: uuid.UUID, alumno_ids: list[uuid.UUID]) -> int:
        """Insert candidates idempotently; skip if already exists. Returns count added."""
        added = 0
        for alumno_id in alumno_ids:
            existing = await self.session.scalar(
                select(CandidatoEvaluacion)
                .where(CandidatoEvaluacion.tenant_id == self.context.tenant_id)
                .where(CandidatoEvaluacion.deleted_at.is_(None))
                .where(CandidatoEvaluacion.evaluacion_id == evaluacion_id)
                .where(CandidatoEvaluacion.alumno_id == alumno_id)
            )
            if existing is None:
                self.session.add(
                    CandidatoEvaluacion(
                        tenant_id=self.context.tenant_id,
                        evaluacion_id=evaluacion_id,
                        alumno_id=alumno_id,
                    )
                )
                added += 1
        await self.session.flush()
        return added

    async def es_candidato(self, evaluacion_id: uuid.UUID, alumno_id: uuid.UUID) -> bool:
        """Return True if alumno is a candidate for the evaluacion."""
        result = await self.session.scalar(
            select(CandidatoEvaluacion)
            .where(CandidatoEvaluacion.tenant_id == self.context.tenant_id)
            .where(CandidatoEvaluacion.deleted_at.is_(None))
            .where(CandidatoEvaluacion.evaluacion_id == evaluacion_id)
            .where(CandidatoEvaluacion.alumno_id == alumno_id)
        )
        return result is not None

    async def count_by_evaluacion(self, evaluacion_id: uuid.UUID) -> int:
        """Count active candidates for an evaluacion."""
        result = await self.session.scalar(
            select(func.count(CandidatoEvaluacion.id))
            .where(CandidatoEvaluacion.tenant_id == self.context.tenant_id)
            .where(CandidatoEvaluacion.deleted_at.is_(None))
            .where(CandidatoEvaluacion.evaluacion_id == evaluacion_id)
        )
        return result or 0


class ReservaEvaluacionRepository(TenantScopedRepository[ReservaEvaluacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=ReservaEvaluacion, tenant_id=tenant_id)

    async def count_activas_por_dia(self, dia_id: uuid.UUID) -> int:
        """Count active reservas for a given DiaEvaluacion."""
        result = await self.session.scalar(
            select(func.count(ReservaEvaluacion.id))
            .where(ReservaEvaluacion.tenant_id == self.context.tenant_id)
            .where(ReservaEvaluacion.deleted_at.is_(None))
            .where(ReservaEvaluacion.dia_evaluacion_id == dia_id)
            .where(ReservaEvaluacion.estado == "Activa")
        )
        return result or 0

    async def tiene_reserva_activa(self, evaluacion_id: uuid.UUID, alumno_id: uuid.UUID) -> bool:
        """Return True if alumno already has an active reserva for this evaluacion."""
        result = await self.session.scalar(
            select(ReservaEvaluacion)
            .where(ReservaEvaluacion.tenant_id == self.context.tenant_id)
            .where(ReservaEvaluacion.deleted_at.is_(None))
            .where(ReservaEvaluacion.evaluacion_id == evaluacion_id)
            .where(ReservaEvaluacion.alumno_id == alumno_id)
            .where(ReservaEvaluacion.estado == "Activa")
        )
        return result is not None

    async def list_activas_por_evaluacion(self, evaluacion_id: uuid.UUID) -> list[ReservaEvaluacion]:
        """List all active reservas for an evaluacion."""
        stmt = (
            self._base_query()
            .where(ReservaEvaluacion.evaluacion_id == evaluacion_id)
            .where(ReservaEvaluacion.estado == "Activa")
            .order_by(ReservaEvaluacion.created_at.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count_activas_tenant(self) -> int:
        """Count total active reservas across the tenant."""
        result = await self.session.scalar(
            select(func.count(ReservaEvaluacion.id))
            .where(ReservaEvaluacion.tenant_id == self.context.tenant_id)
            .where(ReservaEvaluacion.deleted_at.is_(None))
            .where(ReservaEvaluacion.estado == "Activa")
        )
        return result or 0


class ResultadoEvaluacionRepository(TenantScopedRepository[ResultadoEvaluacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=ResultadoEvaluacion, tenant_id=tenant_id)

    async def upsert(
        self, evaluacion_id: uuid.UUID, alumno_id: uuid.UUID, nota_final: str
    ) -> ResultadoEvaluacion:
        """Create or update ResultadoEvaluacion for alumno in evaluacion."""
        existing = await self.session.scalar(
            select(ResultadoEvaluacion)
            .where(ResultadoEvaluacion.tenant_id == self.context.tenant_id)
            .where(ResultadoEvaluacion.deleted_at.is_(None))
            .where(ResultadoEvaluacion.evaluacion_id == evaluacion_id)
            .where(ResultadoEvaluacion.alumno_id == alumno_id)
        )
        if existing is not None:
            existing.nota_final = nota_final
            await self.session.flush()
            return existing
        nuevo = ResultadoEvaluacion(
            tenant_id=self.context.tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=alumno_id,
            nota_final=nota_final,
        )
        self.session.add(nuevo)
        await self.session.flush()
        return nuevo

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> list[ResultadoEvaluacion]:
        stmt = (
            self._base_query()
            .where(ResultadoEvaluacion.evaluacion_id == evaluacion_id)
            .order_by(ResultadoEvaluacion.created_at.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count_tenant(self) -> int:
        """Count total result records across the tenant."""
        result = await self.session.scalar(
            select(func.count(ResultadoEvaluacion.id))
            .where(ResultadoEvaluacion.tenant_id == self.context.tenant_id)
            .where(ResultadoEvaluacion.deleted_at.is_(None))
        )
        return result or 0
