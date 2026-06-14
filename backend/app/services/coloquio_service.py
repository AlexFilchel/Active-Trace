from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.models.evaluaciones import DiaEvaluacion, ReservaEvaluacion
from app.repositories.coloquios import (
    CandidatoEvaluacionRepository,
    DiaEvaluacionRepository,
    EvaluacionRepository,
    ReservaEvaluacionRepository,
    ResultadoEvaluacionRepository,
)
from app.repositories.usuarios import UsuarioRepository
from app.schemas.coloquios import (
    AgendaDiaResponse,
    ConvocatoriaResponse,
    CrearConvocatoriaRequest,
    EditarConvocatoriaRequest,
    MetricasResponse,
    RegistrarResultadoRequest,
    ReservaResponse,
    ResultadoResponse,
)


class ColoquioNotFoundError(Exception):
    """Convocatoria not found within the tenant."""

    status_code = 404

    def __init__(self, detail: str = "Convocatoria no encontrada.") -> None:
        self.detail = detail
        super().__init__(detail)


class NoCandidatoError(Exception):
    """Alumno is not a candidate for the evaluacion."""

    status_code = 403

    def __init__(self, detail: str = "El alumno no es candidato de esta convocatoria.") -> None:
        self.detail = detail
        super().__init__(detail)


class SinCupoError(Exception):
    """No slots available for the requested DiaEvaluacion."""

    status_code = 409

    def __init__(self, detail: str = "Sin cupo disponible para este día.") -> None:
        self.detail = detail
        super().__init__(detail)


class ReservaDuplicadaError(Exception):
    """Alumno already has an active reserva for this evaluacion."""

    status_code = 409

    def __init__(self, detail: str = "El alumno ya tiene una reserva activa en esta convocatoria.") -> None:
        self.detail = detail
        super().__init__(detail)


class ConvocatoriaCerradaError(Exception):
    """Evaluacion is closed; no new reservas accepted."""

    status_code = 409

    def __init__(self, detail: str = "La convocatoria está cerrada.") -> None:
        self.detail = detail
        super().__init__(detail)


class ReservaNoEncontradaError(Exception):
    """Reserva not found or does not belong to the alumno."""

    status_code = 404

    def __init__(self, detail: str = "Reserva no encontrada.") -> None:
        self.detail = detail
        super().__init__(detail)


class ColoquioService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._eval_repo = EvaluacionRepository(session=session, tenant_id=self.tenant_id)
        self._dia_repo = DiaEvaluacionRepository(session=session, tenant_id=self.tenant_id)
        self._candidato_repo = CandidatoEvaluacionRepository(session=session, tenant_id=self.tenant_id)
        self._reserva_repo = ReservaEvaluacionRepository(session=session, tenant_id=self.tenant_id)
        self._resultado_repo = ResultadoEvaluacionRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)

    async def _resolve_alumno_id(self, auth_user_id: uuid.UUID) -> uuid.UUID:
        """Resolve auth_user.id → usuario.id (the domain FK used in candidato/reserva tables)."""
        usuario = await self._usuario_repo.get_by_auth_user_id(auth_user_id)
        if usuario is None:
            raise NoCandidatoError("El alumno no tiene perfil de usuario en este tenant.")
        return usuario.id

    # -------------------------------------------------------------------------
    # Task 4.2 — Crear convocatoria
    # -------------------------------------------------------------------------

    async def crear_convocatoria(
        self,
        *,
        actor_id: uuid.UUID,
        payload: CrearConvocatoriaRequest,
        ip: str | None = None,
    ) -> ConvocatoriaResponse:
        evaluacion = await self._eval_repo.create(
            materia_id=payload.materia_id,
            cohorte_id=payload.cohorte_id,
            instancia=payload.instancia,
            dias_disponibles=len(payload.dias),
            estado="Abierta",
        )

        dias: list[DiaEvaluacion] = [
            DiaEvaluacion(
                tenant_id=self.tenant_id,
                evaluacion_id=evaluacion.id,
                fecha=dia.fecha,
                cupo_total=dia.cupo_total,
            )
            for dia in payload.dias
        ]
        await self._dia_repo.bulk_create(dias)

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="COLOQUIO_CREAR",
            filas_afectadas=len(dias),
            detalle={"evaluacion_id": str(evaluacion.id), "dias": len(dias)},
            ip=ip,
        )

        return ConvocatoriaResponse(
            id=evaluacion.id,
            tenant_id=evaluacion.tenant_id,
            materia_id=evaluacion.materia_id,
            cohorte_id=evaluacion.cohorte_id,
            tipo=evaluacion.tipo,
            instancia=evaluacion.instancia,
            dias_disponibles=evaluacion.dias_disponibles,
            estado=evaluacion.estado,
            created_at=evaluacion.created_at,
            convocados=0,
            reservas_activas=0,
            cupos_libres=sum(d.cupo_total for d in dias),
        )

    # -------------------------------------------------------------------------
    # Task 4.3 — Importar candidatos
    # -------------------------------------------------------------------------

    async def importar_candidatos(
        self,
        *,
        actor_id: uuid.UUID,
        evaluacion_id: uuid.UUID,
        alumno_ids: list[uuid.UUID],
        ip: str | None = None,
    ) -> int:
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ColoquioNotFoundError()
        added = await self._candidato_repo.upsert_many(evaluacion_id, alumno_ids)
        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="COLOQUIO_IMPORTAR_CANDIDATOS",
            filas_afectadas=added,
            detalle={"evaluacion_id": str(evaluacion_id), "total": len(alumno_ids)},
            ip=ip,
        )
        return added

    # -------------------------------------------------------------------------
    # Task 4.4 — Reservar turno
    # -------------------------------------------------------------------------

    async def reservar(
        self,
        *,
        actor_id_alumno: uuid.UUID,
        evaluacion_id: uuid.UUID,
        dia_evaluacion_id: uuid.UUID,
        ip: str | None = None,
    ) -> ReservaResponse:
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ColoquioNotFoundError()
        if evaluacion.estado == "Cerrada":
            raise ConvocatoriaCerradaError()

        alumno_id = await self._resolve_alumno_id(actor_id_alumno)

        candidato = await self._candidato_repo.es_candidato(evaluacion_id, alumno_id)
        if not candidato:
            raise NoCandidatoError()

        # Row-level lock on the day
        dia = await self._dia_repo.get_for_update(dia_evaluacion_id)
        if dia is None:
            raise ColoquioNotFoundError("Día de evaluación no encontrado.")

        activas = await self._reserva_repo.count_activas_por_dia(dia_evaluacion_id)
        if activas >= dia.cupo_total:
            raise SinCupoError()

        duplicada = await self._reserva_repo.tiene_reserva_activa(evaluacion_id, alumno_id)
        if duplicada:
            raise ReservaDuplicadaError()

        reserva = await self._reserva_repo.create(
            evaluacion_id=evaluacion_id,
            dia_evaluacion_id=dia_evaluacion_id,
            alumno_id=alumno_id,
            estado="Activa",
        )

        await audit_action(
            session=self.session,
            actor_id=actor_id_alumno,
            tenant_id=self.tenant_id,
            accion="COLOQUIO_RESERVAR",
            filas_afectadas=1,
            detalle={"reserva_id": str(reserva.id), "evaluacion_id": str(evaluacion_id)},
            ip=ip,
        )

        return ReservaResponse.model_validate(reserva)

    # -------------------------------------------------------------------------
    # Task 4.5 — Cancelar reserva
    # -------------------------------------------------------------------------

    async def cancelar_reserva(
        self,
        *,
        actor_id_alumno: uuid.UUID,
        reserva_id: uuid.UUID,
        ip: str | None = None,
    ) -> ReservaResponse:
        alumno_id = await self._resolve_alumno_id(actor_id_alumno)
        reserva = await self._reserva_repo.get(reserva_id)
        if reserva is None or reserva.alumno_id != alumno_id:
            raise ReservaNoEncontradaError()

        reserva.estado = "Cancelada"
        await self.session.flush()

        await audit_action(
            session=self.session,
            actor_id=actor_id_alumno,
            tenant_id=self.tenant_id,
            accion="COLOQUIO_CANCELAR_RESERVA",
            filas_afectadas=1,
            detalle={"reserva_id": str(reserva_id)},
            ip=ip,
        )

        return ReservaResponse.model_validate(reserva)

    # -------------------------------------------------------------------------
    # Task 4.6 — Listar convocatorias con métricas
    # -------------------------------------------------------------------------

    async def listar_convocatorias(self) -> list[ConvocatoriaResponse]:
        evaluaciones = await self._eval_repo.list()
        result: list[ConvocatoriaResponse] = []
        for ev in evaluaciones:
            convocados = await self._candidato_repo.count_by_evaluacion(ev.id)
            dias = await self._dia_repo.list_by_evaluacion(ev.id)
            cupo_total_sum = sum(d.cupo_total for d in dias)
            reservas_activas = 0
            for d in dias:
                reservas_activas += await self._reserva_repo.count_activas_por_dia(d.id)
            cupos_libres = cupo_total_sum - reservas_activas
            result.append(
                ConvocatoriaResponse(
                    id=ev.id,
                    tenant_id=ev.tenant_id,
                    materia_id=ev.materia_id,
                    cohorte_id=ev.cohorte_id,
                    tipo=ev.tipo,
                    instancia=ev.instancia,
                    dias_disponibles=ev.dias_disponibles,
                    estado=ev.estado,
                    created_at=ev.created_at,
                    convocados=convocados,
                    reservas_activas=reservas_activas,
                    cupos_libres=cupos_libres,
                )
            )
        return result

    # -------------------------------------------------------------------------
    # Task 4.7 — Panel de métricas
    # -------------------------------------------------------------------------

    async def metricas(self) -> MetricasResponse:
        evaluaciones = await self._eval_repo.list()
        convocados = 0
        for ev in evaluaciones:
            convocados += await self._candidato_repo.count_by_evaluacion(ev.id)
        instancias_activas = sum(1 for ev in evaluaciones if ev.estado == "Abierta")
        reservas_activas = await self._reserva_repo.count_activas_tenant()
        notas_registradas = await self._resultado_repo.count_tenant()
        return MetricasResponse(
            convocados=convocados,
            instancias_activas=instancias_activas,
            reservas_activas=reservas_activas,
            notas_registradas=notas_registradas,
        )

    # -------------------------------------------------------------------------
    # Task 4.8 — Editar convocatoria + agenda
    # -------------------------------------------------------------------------

    async def editar_convocatoria(
        self,
        evaluacion_id: uuid.UUID,
        payload: EditarConvocatoriaRequest,
    ):
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ColoquioNotFoundError()

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(evaluacion, field, value)
        await self.session.flush()

        return ConvocatoriaResponse(
            id=evaluacion.id,
            tenant_id=evaluacion.tenant_id,
            materia_id=evaluacion.materia_id,
            cohorte_id=evaluacion.cohorte_id,
            tipo=evaluacion.tipo,
            instancia=evaluacion.instancia,
            dias_disponibles=evaluacion.dias_disponibles,
            estado=evaluacion.estado,
            created_at=evaluacion.created_at,
        )

    async def agenda(self, evaluacion_id: uuid.UUID) -> list[AgendaDiaResponse]:
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ColoquioNotFoundError()

        reservas = await self._reserva_repo.list_activas_por_evaluacion(evaluacion_id)
        dias = await self._dia_repo.list_by_evaluacion(evaluacion_id)

        # Build a map: dia_id -> fecha
        dia_fecha: dict[uuid.UUID, object] = {d.id: d.fecha for d in dias}

        # Group reservas by dia_evaluacion_id
        grupos: dict[uuid.UUID, list[ReservaEvaluacion]] = defaultdict(list)
        for r in reservas:
            grupos[r.dia_evaluacion_id].append(r)

        result: list[AgendaDiaResponse] = []
        for dia in dias:
            reservas_dia = grupos.get(dia.id, [])
            result.append(
                AgendaDiaResponse(
                    fecha=dia.fecha,
                    reservas=[ReservaResponse.model_validate(r) for r in reservas_dia],
                )
            )
        return result

    # -------------------------------------------------------------------------
    # Task 4.9 — Registrar / listar resultados
    # -------------------------------------------------------------------------

    async def registrar_resultado(
        self,
        *,
        actor_id: uuid.UUID,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        nota_final: str,
        ip: str | None = None,
    ) -> ResultadoResponse:
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ColoquioNotFoundError()

        resultado = await self._resultado_repo.upsert(evaluacion_id, alumno_id, nota_final)

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="COLOQUIO_REGISTRAR_RESULTADO",
            filas_afectadas=1,
            detalle={"evaluacion_id": str(evaluacion_id), "alumno_id": str(alumno_id)},
            ip=ip,
        )

        return ResultadoResponse.model_validate(resultado)

    async def listar_resultados(self, evaluacion_id: uuid.UUID) -> list[ResultadoResponse]:
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ColoquioNotFoundError()

        resultados = await self._resultado_repo.list_by_evaluacion(evaluacion_id)
        return [ResultadoResponse.model_validate(r) for r in resultados]
