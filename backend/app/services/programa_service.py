from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.repositories.estructura import MateriaRepository
from app.repositories.programas import FechaAcademicaRepository, ProgramaRepository
from app.schemas.programas import (
    CrearFechaAcademicaRequest,
    CrearProgramaRequest,
    EditarFechaAcademicaRequest,
    FechaAcademicaResponse,
    FragmentoLmsResponse,
    ProgramaResponse,
)


class FechaAcademicaNotFoundError(Exception):
    status_code = 404

    def __init__(self, detail: str = "Fecha académica no encontrada.") -> None:
        self.detail = detail
        super().__init__(detail)


def _ordinal(n: int) -> str:
    sufijos = {1: "er", 2: "do", 3: "er", 4: "to", 5: "to", 6: "to", 7: "mo", 8: "vo", 9: "no"}
    return f"{n}{sufijos.get(n, 'mo')}"


class ProgramaService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._programa_repo = ProgramaRepository(session=session, tenant_id=self.tenant_id)
        self._fecha_repo = FechaAcademicaRepository(session=session, tenant_id=self.tenant_id)
        self._materia_repo = MateriaRepository(session=session, tenant_id=self.tenant_id)

    async def crear_programa(
        self,
        *,
        actor_id: uuid.UUID,
        payload: CrearProgramaRequest,
        ip: str | None = None,
    ) -> ProgramaResponse:
        programa = await self._programa_repo.create(
            materia_id=payload.materia_id,
            carrera_id=payload.carrera_id,
            cohorte_id=payload.cohorte_id,
            titulo=payload.titulo,
            referencia_archivo=payload.referencia_archivo,
        )
        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="PROGRAMA_CREAR",
            filas_afectadas=1,
            detalle={"programa_id": str(programa.id)},
            ip=ip,
        )
        return ProgramaResponse.model_validate(programa, from_attributes=True)

    async def listar_programas(
        self,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[ProgramaResponse]:
        programas = await self._programa_repo.list_filtrado(
            materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id
        )
        return [ProgramaResponse.model_validate(p, from_attributes=True) for p in programas]

    async def crear_fecha(
        self,
        *,
        actor_id: uuid.UUID,
        payload: CrearFechaAcademicaRequest,
        ip: str | None = None,
    ) -> FechaAcademicaResponse:
        fecha = await self._fecha_repo.create(
            materia_id=payload.materia_id,
            cohorte_id=payload.cohorte_id,
            tipo=payload.tipo,
            numero=payload.numero,
            periodo=payload.periodo,
            fecha=payload.fecha,
            titulo=payload.titulo,
        )
        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="FECHA_ACAT_CREAR",
            filas_afectadas=1,
            detalle={"fecha_id": str(fecha.id)},
            ip=ip,
        )
        return FechaAcademicaResponse.model_validate(fecha, from_attributes=True)

    async def editar_fecha(
        self,
        *,
        actor_id: uuid.UUID,
        fecha_id: uuid.UUID,
        payload: EditarFechaAcademicaRequest,
        ip: str | None = None,
    ) -> FechaAcademicaResponse:
        cambios = payload.model_dump(exclude_unset=True)
        fecha = await self._fecha_repo.update(fecha_id, **cambios)
        if fecha is None:
            raise FechaAcademicaNotFoundError()
        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="FECHA_ACAT_EDITAR",
            filas_afectadas=1,
            detalle={"fecha_id": str(fecha_id), "cambios": list(cambios.keys())},
            ip=ip,
        )
        return FechaAcademicaResponse.model_validate(fecha, from_attributes=True)

    async def listar_fechas(
        self,
        materia_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        tipo: str | None = None,
        periodo: str | None = None,
    ) -> list[FechaAcademicaResponse]:
        fechas = await self._fecha_repo.list_filtrado(
            materia_id=materia_id, cohorte_id=cohorte_id, tipo=tipo, periodo=periodo
        )
        return [FechaAcademicaResponse.model_validate(f, from_attributes=True) for f in fechas]

    async def generar_fragmento_lms(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
    ) -> FragmentoLmsResponse:
        fechas = await self._fecha_repo.list_filtrado(
            materia_id=materia_id, cohorte_id=cohorte_id, periodo=periodo
        )
        if not fechas:
            return FragmentoLmsResponse(texto="")
        materia = await self._materia_repo.get(materia_id)
        nombre_materia = materia.nombre if materia else str(materia_id)
        lineas = [f"**Fechas de evaluación — {nombre_materia} — {periodo}**", ""]
        for f in fechas:
            lineas.append(
                f"📅 {_ordinal(f.numero)} {f.tipo}: {f.fecha.strftime('%d/%m/%Y')} — {f.titulo}"
            )
        return FragmentoLmsResponse(texto="\n".join(lineas))
