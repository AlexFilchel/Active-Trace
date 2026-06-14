from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.models.usuarios import Asignacion
from app.repositories.encuentros import GuardiaRepository
from app.schemas.guardias import RegistrarGuardiaRequest


class GuardiaNotFoundError(Exception):
    """Raised when a resource is not found within the tenant."""

    status_code = 404

    def __init__(self, detail: str = "Recurso no encontrado.") -> None:
        self.detail = detail
        super().__init__(detail)


class GuardiaService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._repo = GuardiaRepository(session=session, tenant_id=self.tenant_id)

    async def _validar_asignacion(self, asignacion_id: uuid.UUID) -> None:
        """Raise GuardiaNotFoundError if asignacion_id does not belong to this tenant."""
        stmt = (
            select(Asignacion)
            .where(Asignacion.tenant_id == self.tenant_id)
            .where(Asignacion.deleted_at.is_(None))
            .where(Asignacion.id == asignacion_id)
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise GuardiaNotFoundError("Asignación no encontrada en el tenant.")

    async def registrar(
        self,
        *,
        actor_id: uuid.UUID,
        payload: RegistrarGuardiaRequest,
        ip: str | None = None,
    ) -> object:
        """Register a guardia and audit the action."""
        await self._validar_asignacion(payload.asignacion_id)

        guardia = await self._repo.create(
            asignacion_id=payload.asignacion_id,
            materia_id=payload.materia_id,
            carrera_id=payload.carrera_id,
            cohorte_id=payload.cohorte_id,
            dia=payload.dia,
            horario=payload.horario,
            estado="Pendiente",
            comentarios=payload.comentarios,
            creada_at=datetime.now(timezone.utc),
        )

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="GUARDIA_REGISTRAR",
            filas_afectadas=1,
            materia_id=payload.materia_id,
            detalle={"guardia_id": str(guardia.id)},
            ip=ip,
        )
        return guardia

    async def listar(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        estado: str | None = None,
    ) -> list[object]:
        """List guardias with optional filters."""
        return await self._repo.list_filtered(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            estado=estado,
        )

    async def exportar(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        estado: str | None = None,
    ) -> str:
        """Export guardias as a CSV string.

        Columns: usuario_id, materia, carrera, cohorte, dia, horario, estado, comentarios
        If no guardias match, returns CSV with only headers.
        """
        guardias = await self._repo.list_filtered(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            estado=estado,
        )

        output = io.StringIO()
        fieldnames = ["usuario_id", "materia_id", "carrera_id", "cohorte_id", "dia", "horario", "estado", "comentarios"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for g in guardias:
            writer.writerow(
                {
                    "usuario_id": str(g.asignacion_id),
                    "materia_id": str(g.materia_id),
                    "carrera_id": str(g.carrera_id),
                    "cohorte_id": str(g.cohorte_id),
                    "dia": str(g.dia),
                    "horario": g.horario,
                    "estado": g.estado,
                    "comentarios": g.comentarios or "",
                }
            )

        return output.getvalue()
