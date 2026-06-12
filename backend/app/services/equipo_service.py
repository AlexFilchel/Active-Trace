from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.models.usuarios import Asignacion
from app.repositories.estructura import CarreraRepository, CohorteRepository, MateriaRepository
from app.repositories.rbac import RbacRepository
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository
from app.schemas.equipos import (
    AsignacionMasivaRequest,
    ClonarEquipoRequest,
    DocenteBusquedaItem,
    MisEquiposItem,
    VigenciaEquipoRequest,
)
from app.services.usuarios import ConflictError, NotFoundError


class EquipoService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str):
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=self.tenant_id)
        self._rbac_repo = RbacRepository(session=session, tenant_id=self.tenant_id)
        self._carrera_repo = CarreraRepository(session=session, tenant_id=self.tenant_id)
        self._cohorte_repo = CohorteRepository(session=session, tenant_id=self.tenant_id)
        self._materia_repo = MateriaRepository(session=session, tenant_id=self.tenant_id)

    async def get_mis_equipos(self, auth_user_id: uuid.UUID) -> list[MisEquiposItem]:
        usuario = await self._usuario_repo.get_by_auth_user_id(auth_user_id)
        if usuario is None:
            return []

        asignaciones = await self._asignacion_repo.get_by_usuario(usuario.id)
        if not asignaciones:
            return []

        materia_ids = {a.materia_id for a in asignaciones if a.materia_id}
        carrera_ids = {a.carrera_id for a in asignaciones if a.carrera_id}
        cohorte_ids = {a.cohorte_id for a in asignaciones if a.cohorte_id}
        rol_ids = {a.rol_id for a in asignaciones}

        materias = {m.id: m.nombre for m in await self._materia_repo.list() if m.id in materia_ids}
        carreras = {c.id: c.nombre for c in await self._carrera_repo.list() if c.id in carrera_ids}
        cohortes = {c.id: c.nombre for c in await self._cohorte_repo.list() if c.id in cohorte_ids}
        roles_all = await self._rbac_repo.list()
        roles = {r.id: r.nombre for r in roles_all if r.id in rol_ids}

        result = []
        for a in asignaciones:
            result.append(
                MisEquiposItem(
                    id=a.id,
                    usuario_id=a.usuario_id,
                    rol_id=a.rol_id,
                    rol_nombre=roles.get(a.rol_id),
                    materia_id=a.materia_id,
                    materia_nombre=materias.get(a.materia_id) if a.materia_id else None,
                    carrera_id=a.carrera_id,
                    carrera_nombre=carreras.get(a.carrera_id) if a.carrera_id else None,
                    cohorte_id=a.cohorte_id,
                    cohorte_nombre=cohortes.get(a.cohorte_id) if a.cohorte_id else None,
                    comisiones=a.comisiones,
                    desde=a.desde,
                    hasta=a.hasta,
                    estado_vigencia=a.estado_vigencia,
                )
            )
        return result

    async def list_asignaciones(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        rol_id: uuid.UUID | None = None,
        usuario_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[Asignacion]:
        return await self._asignacion_repo.list_by_equipo(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            rol_id=rol_id,
            usuario_id=usuario_id,
            active_only=active_only,
        )

    async def buscar_docentes(self, q: str) -> list[DocenteBusquedaItem]:
        usuarios = await self._usuario_repo.search_docentes(q)
        return [
            DocenteBusquedaItem(
                id=u.id,
                nombre=u.nombre,
                apellidos=u.apellidos,
                legajo=u.legajo,
            )
            for u in usuarios
        ]

    async def asignacion_masiva(
        self,
        *,
        actor_id: uuid.UUID,
        payload: AsignacionMasivaRequest,
        ip: str | None = None,
    ) -> int:
        for uid in payload.usuario_ids:
            existing = await self._asignacion_repo.list(
                usuario_id=uid,
                rol_id=payload.rol_id,
                materia_id=payload.materia_id,
                carrera_id=payload.carrera_id,
                cohorte_id=payload.cohorte_id,
                active_only=True,
            )
            if existing:
                raise ConflictError(f"El usuario {uid} ya tiene una asignación vigente en este contexto.")

        nuevas = [
            Asignacion(
                tenant_id=self.tenant_id,
                usuario_id=uid,
                rol_id=payload.rol_id,
                materia_id=payload.materia_id,
                carrera_id=payload.carrera_id,
                cohorte_id=payload.cohorte_id,
                responsable_id=payload.responsable_id,
                comisiones=payload.comisiones,
                desde=payload.desde,
                hasta=payload.hasta,
            )
            for uid in payload.usuario_ids
        ]

        try:
            await self._asignacion_repo.bulk_create(nuevas)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("No se pudo crear alguna asignación por conflicto de integridad.") from exc

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="ASIGNACION_MODIFICAR",
            detalle={"operacion": "masiva", "cantidad": len(nuevas)},
            filas_afectadas=len(nuevas),
            ip=ip,
        )
        return len(nuevas)

    async def clonar_equipo(
        self,
        *,
        actor_id: uuid.UUID,
        payload: ClonarEquipoRequest,
        ip: str | None = None,
    ) -> int:
        vigentes = await self._asignacion_repo.get_vigentes_by_equipo(
            materia_id=payload.origen.materia_id,
            carrera_id=payload.origen.carrera_id,
            cohorte_id=payload.origen.cohorte_id,
        )
        if not vigentes:
            raise NotFoundError("El equipo origen no tiene asignaciones vigentes para clonar.")

        clones = [
            Asignacion(
                tenant_id=self.tenant_id,
                usuario_id=a.usuario_id,
                rol_id=a.rol_id,
                materia_id=payload.destino.materia_id,
                carrera_id=payload.destino.carrera_id,
                cohorte_id=payload.destino.cohorte_id,
                responsable_id=a.responsable_id,
                comisiones=list(a.comisiones),
                desde=payload.destino.desde,
                hasta=payload.destino.hasta,
            )
            for a in vigentes
        ]

        try:
            await self._asignacion_repo.bulk_create(clones)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Error al clonar: conflicto de integridad en alguna asignación.") from exc

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="ASIGNACION_MODIFICAR",
            detalle={"operacion": "clonar", "cantidad": len(clones)},
            filas_afectadas=len(clones),
            ip=ip,
        )
        return len(clones)

    async def modificar_vigencia_equipo(
        self,
        *,
        actor_id: uuid.UUID,
        payload: VigenciaEquipoRequest,
        ip: str | None = None,
    ) -> int:
        rows = await self._asignacion_repo.bulk_update_vigencia(
            materia_id=payload.materia_id,
            carrera_id=payload.carrera_id,
            cohorte_id=payload.cohorte_id,
            desde=payload.desde,
            hasta=payload.hasta,
        )
        if rows == 0:
            raise NotFoundError("No se encontraron asignaciones para el equipo indicado.")

        await audit_action(
            session=self.session,
            actor_id=actor_id,
            tenant_id=self.tenant_id,
            accion="ASIGNACION_MODIFICAR",
            detalle={"operacion": "vigencia_masiva"},
            filas_afectadas=rows,
            ip=ip,
        )
        return rows

    async def exportar_equipo(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> str:
        asignaciones = await self._asignacion_repo.list_by_equipo(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )

        roles_all = await self._rbac_repo.list()
        roles = {r.id: r.nombre for r in roles_all}
        materias = {m.id: m.nombre for m in await self._materia_repo.list()}
        carreras = {c.id: c.nombre for c in await self._carrera_repo.list()}
        cohortes = {c.id: c.nombre for c in await self._cohorte_repo.list()}

        output = io.StringIO()
        fieldnames = ["usuario_id", "rol", "materia", "carrera", "cohorte", "desde", "hasta", "estado_vigencia"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for a in asignaciones:
            writer.writerow(
                {
                    "usuario_id": str(a.usuario_id),
                    "rol": roles.get(a.rol_id, str(a.rol_id)),
                    "materia": materias.get(a.materia_id, "") if a.materia_id else "",
                    "carrera": carreras.get(a.carrera_id, "") if a.carrera_id else "",
                    "cohorte": cohortes.get(a.cohorte_id, "") if a.cohorte_id else "",
                    "desde": str(a.desde),
                    "hasta": str(a.hasta) if a.hasta else "",
                    "estado_vigencia": a.estado_vigencia,
                }
            )

        return output.getvalue()

    def _get_ip(self, request: Any) -> str | None:
        try:
            return request.client.host
        except AttributeError:
            return None
