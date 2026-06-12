from __future__ import annotations

import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion
from app.models.padron import EntradaPadron, VersionPadron
from app.repositories.tenant_scoped import TenantScopedRepository


class CalificacionRepository(TenantScopedRepository[Calificacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Calificacion, tenant_id=tenant_id)

    async def upsert_bulk(self, calificaciones: list[dict]) -> int:
        """Bulk-insert with ON CONFLICT DO UPDATE. Returns rowcount."""
        if not calificaciones:
            return 0

        for row in calificaciones:
            row["tenant_id"] = self.context.tenant_id

        stmt = (
            insert(Calificacion)
            .values(calificaciones)
            .on_conflict_do_update(
                constraint="uq_calificacion_entrada_actividad_actor",
                set_={
                    "nota_numerica": text("EXCLUDED.nota_numerica"),
                    "nota_textual": text("EXCLUDED.nota_textual"),
                    "aprobado": text("EXCLUDED.aprobado"),
                    "updated_at": text("now()"),
                    "deleted_at": None,
                },
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_by_actor_materia(
        self,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> int:
        """Delete calificaciones from actor scoped to materia (RN-04). Returns count."""
        entrada_ids_subq = (
            select(EntradaPadron.id)
            .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
            .where(EntradaPadron.tenant_id == self.context.tenant_id)
            .where(VersionPadron.materia_id == materia_id)
        )

        stmt = (
            delete(Calificacion)
            .where(Calificacion.tenant_id == self.context.tenant_id)
            .where(Calificacion.actor_id == actor_id)
            .where(Calificacion.entrada_padron_id.in_(entrada_ids_subq))
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_sin_calificar_textual(
        self,
        version_id: uuid.UUID,
        actividades_textuales: list[str],
    ) -> list[dict]:
        """Return alumnos with no textual calificacion for given actividades."""
        if not actividades_textuales:
            return []

        results = []
        for actividad in actividades_textuales:
            existing_subq = (
                select(Calificacion.entrada_padron_id)
                .where(Calificacion.tenant_id == self.context.tenant_id)
                .where(Calificacion.actividad == actividad)
                .where(Calificacion.nota_textual.isnot(None))
                .where(Calificacion.deleted_at.is_(None))
            )
            stmt = (
                select(EntradaPadron)
                .where(EntradaPadron.version_id == version_id)
                .where(EntradaPadron.tenant_id == self.context.tenant_id)
                .where(EntradaPadron.deleted_at.is_(None))
                .where(EntradaPadron.id.notin_(existing_subq))
            )
            rows = await self.session.scalars(stmt)
            for ep in rows.all():
                results.append({
                    "entrada_padron_id": ep.id,
                    "nombre": ep.nombre,
                    "apellidos": ep.apellidos,
                    "actividad": actividad,
                })
        return results
