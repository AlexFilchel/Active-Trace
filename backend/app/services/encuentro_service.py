from __future__ import annotations

import html
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.models.encuentros import InstanciaEncuentro, SlotEncuentro
from app.models.usuarios import Asignacion
from app.repositories.encuentros import InstanciaEncuentroRepository, SlotEncuentroRepository
from app.schemas.encuentros import CrearRecurrenteRequest, CrearUnicoRequest, EditarInstanciaRequest


class EncuentroNotFoundError(Exception):
    """Raised when an instancia_encuentro is not found in the tenant."""

    status_code = 404

    def __init__(self, detail: str = "Instancia no encontrada.") -> None:
        self.detail = detail
        super().__init__(detail)


class EncuentroService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._slot_repo = SlotEncuentroRepository(session=session, tenant_id=self.tenant_id)
        self._instancia_repo = InstanciaEncuentroRepository(session=session, tenant_id=self.tenant_id)

    async def _validar_asignacion(self, asignacion_id: uuid.UUID) -> None:
        """Raise EncuentroNotFoundError if asignacion_id does not belong to this tenant."""
        stmt = (
            select(Asignacion)
            .where(Asignacion.tenant_id == self.tenant_id)
            .where(Asignacion.deleted_at.is_(None))
            .where(Asignacion.id == asignacion_id)
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise EncuentroNotFoundError("Asignación no encontrada en el tenant.")

    async def crear_recurrente(
        self,
        *,
        actor_id: uuid.UUID,
        payload: CrearRecurrenteRequest,
        ip: str | None = None,
    ) -> tuple[SlotEncuentro, list[InstanciaEncuentro]]:
        """Create a recurring slot + N InstanciaEncuentro.

        All created atomically (single transaction flush).
        """
        await self._validar_asignacion(payload.asignacion_id)

        slot = await self._slot_repo.create(
            asignacion_id=payload.asignacion_id,
            materia_id=payload.materia_id,
            titulo=payload.titulo,
            hora=payload.hora,
            dia_semana=payload.dia_semana,
            fecha_inicio=payload.fecha_inicio,
            cant_semanas=payload.cant_semanas,
            fecha_unica=None,
            meet_url=payload.meet_url,
        )

        instancias: list[InstanciaEncuentro] = [
            InstanciaEncuentro(
                tenant_id=self.tenant_id,
                slot_id=slot.id,
                materia_id=payload.materia_id,
                fecha=payload.fecha_inicio + timedelta(weeks=k),
                hora=payload.hora,
                titulo=payload.titulo,
                estado="Programado",
                meet_url=payload.meet_url,
            )
            for k in range(payload.cant_semanas)
        ]
        await self._instancia_repo.bulk_create(instancias)

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="ENCUENTRO_GESTIONAR",
            filas_afectadas=len(instancias),
            materia_id=payload.materia_id,
            detalle={"slot_id": str(slot.id), "cant_semanas": payload.cant_semanas},
            ip=ip,
        )
        return slot, instancias

    async def crear_unico(
        self,
        *,
        actor_id: uuid.UUID,
        payload: CrearUnicoRequest,
        ip: str | None = None,
    ) -> tuple[SlotEncuentro, InstanciaEncuentro]:
        """Create a one-off encounter (slot with cant_semanas=0 + 1 instancia)."""
        await self._validar_asignacion(payload.asignacion_id)

        slot = await self._slot_repo.create(
            asignacion_id=payload.asignacion_id,
            materia_id=payload.materia_id,
            titulo=payload.titulo,
            hora=payload.hora,
            dia_semana=payload.fecha.weekday(),
            fecha_inicio=payload.fecha,
            cant_semanas=0,
            fecha_unica=payload.fecha,
            meet_url=payload.meet_url,
        )

        instancia = InstanciaEncuentro(
            tenant_id=self.tenant_id,
            slot_id=slot.id,
            materia_id=payload.materia_id,
            fecha=payload.fecha,
            hora=payload.hora,
            titulo=payload.titulo,
            estado="Programado",
            meet_url=payload.meet_url,
        )
        await self._instancia_repo.bulk_create([instancia])

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="ENCUENTRO_GESTIONAR",
            filas_afectadas=1,
            materia_id=payload.materia_id,
            detalle={"slot_id": str(slot.id), "tipo": "unico"},
            ip=ip,
        )
        return slot, instancia

    async def editar_instancia(
        self,
        instancia_id: uuid.UUID,
        payload: EditarInstanciaRequest,
    ) -> InstanciaEncuentro:
        """Update only the 4 allowed fields; raise EncuentroNotFoundError if absent."""
        instancia = await self._instancia_repo.get(instancia_id)
        if instancia is None:
            raise EncuentroNotFoundError()

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(instancia, field, value)
        await self.session.flush()
        return instancia

    async def listar_encuentros(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        estado: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[InstanciaEncuentro]:
        """Admin view: all instancias in the tenant with optional filters."""
        return await self._instancia_repo.list_filtered(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            estado=estado,
            desde=desde,
            hasta=hasta,
        )

    async def generar_bloque_html(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID | None = None,
    ) -> str:
        """Generate an HTML table fragment with encuentros for a materia.

        Returns empty string (no rows) when there are no instancias.
        All user-supplied content is escaped with html.escape.
        """
        instancias = await self._instancia_repo.list_by_materia(materia_id)

        if not instancias:
            return "<table><thead><tr><th>Título</th><th>Fecha</th><th>Hora</th><th>Enlace</th><th>Grabación</th></tr></thead><tbody></tbody></table>"

        rows_html = ""
        for inst in instancias:
            titulo_esc = html.escape(inst.titulo)
            fecha_esc = html.escape(str(inst.fecha))
            hora_esc = html.escape(str(inst.hora))

            if inst.meet_url:
                url_esc = html.escape(inst.meet_url)
                meet_cell = f'<a href="{url_esc}">{url_esc}</a>'
            else:
                meet_cell = ""

            if inst.video_url:
                video_esc = html.escape(inst.video_url)
                video_cell = f'<a href="{video_esc}">{video_esc}</a>'
            else:
                video_cell = ""

            rows_html += (
                f"<tr>"
                f"<td>{titulo_esc}</td>"
                f"<td>{fecha_esc}</td>"
                f"<td>{hora_esc}</td>"
                f"<td>{meet_cell}</td>"
                f"<td>{video_cell}</td>"
                f"</tr>"
            )

        return (
            "<table>"
            "<thead><tr><th>Título</th><th>Fecha</th><th>Hora</th><th>Enlace</th><th>Grabación</th></tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table>"
        )
