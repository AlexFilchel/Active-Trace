from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_action
from app.repositories.tareas import ComentarioTareaRepository, TareaRepository
from app.repositories.usuarios import UsuarioRepository
from app.schemas.tareas import (
    ComentarioResponse,
    CrearComentarioRequest,
    CrearTareaRequest,
    TareaResponse,
)


# States from which each target state is reachable
_TRANSICIONES_VALIDAS: dict[str, list[str]] = {
    "Pendiente": ["En progreso", "Cancelada"],
    "En progreso": ["Resuelta", "Cancelada"],
    "Resuelta": [],
    "Cancelada": [],
}

# Only asignador or COORD/ADMIN can cancel
_SOLO_ASIGNADOR: set[str] = {"Cancelada"}
_ROLES_ADMIN = {"COORDINADOR", "ADMIN"}


class TareaNotFoundError(Exception):
    status_code = 404

    def __init__(self, detail: str = "Tarea no encontrada.") -> None:
        self.detail = detail
        super().__init__(detail)


class TareaTransicionInvalidaError(Exception):
    status_code = 422

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class TareaService:
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
        self._tarea_repo = TareaRepository(session=session, tenant_id=self.tenant_id)
        self._comentario_repo = ComentarioTareaRepository(session=session, tenant_id=self.tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=self.tenant_id)

    async def _resolve_usuario(self, auth_user_id: uuid.UUID) -> uuid.UUID:
        usuario = await self._usuario_repo.get_by_auth_user_id(auth_user_id)
        if usuario is None:
            raise TareaNotFoundError("El usuario no tiene perfil en este tenant.")
        return usuario.id

    def _transicion_valida(
        self,
        *,
        estado_actual: str,
        nuevo_estado: str,
        actor_usuario_id: uuid.UUID,
        tarea,
        roles: list[str],
    ) -> bool:
        if nuevo_estado not in _TRANSICIONES_VALIDAS.get(estado_actual, []):
            return False
        es_admin = bool(set(roles) & _ROLES_ADMIN)
        es_asignador = actor_usuario_id == tarea.asignado_por
        es_asignado = actor_usuario_id == tarea.asignado_a
        if nuevo_estado in _SOLO_ASIGNADOR:
            return es_asignador or es_admin
        return es_asignador or es_asignado or es_admin

    # ------------------------------------------------------------------
    # 4.2 — Crear tarea
    # ------------------------------------------------------------------

    async def crear_tarea(
        self,
        *,
        actor_auth_id: uuid.UUID,
        payload: CrearTareaRequest,
        ip: str | None = None,
    ) -> TareaResponse:
        actor_id = await self._resolve_usuario(actor_auth_id)
        tarea = await self._tarea_repo.create(
            asignado_a=payload.asignado_a,
            asignado_por=actor_id,
            descripcion=payload.descripcion,
            materia_id=payload.materia_id,
            contexto_id=payload.contexto_id,
            estado="Pendiente",
        )
        await audit_action(
            session=self.session,
            actor_id=actor_auth_id,
            tenant_id=self.tenant_id,
            accion="TAREA_CREAR",
            filas_afectadas=1,
            detalle={"tarea_id": str(tarea.id)},
            ip=ip,
        )
        return TareaResponse.model_validate(tarea, from_attributes=True)

    # ------------------------------------------------------------------
    # 4.3 — Cambiar estado
    # ------------------------------------------------------------------

    async def cambiar_estado(
        self,
        *,
        actor_auth_id: uuid.UUID,
        tarea_id: uuid.UUID,
        nuevo_estado: str,
        roles: list[str],
        ip: str | None = None,
    ) -> TareaResponse:
        tarea = await self._tarea_repo.get(tarea_id)
        if tarea is None:
            raise TareaNotFoundError()
        actor_id = await self._resolve_usuario(actor_auth_id)
        estado_anterior = tarea.estado
        if not self._transicion_valida(
            estado_actual=estado_anterior,
            nuevo_estado=nuevo_estado,
            actor_usuario_id=actor_id,
            tarea=tarea,
            roles=roles,
        ):
            raise TareaTransicionInvalidaError(
                f"Transición '{estado_anterior}' → '{nuevo_estado}' no permitida."
            )
        tarea.estado = nuevo_estado
        await self.session.flush()
        await audit_action(
            session=self.session,
            actor_id=actor_auth_id,
            tenant_id=self.tenant_id,
            accion="TAREA_ESTADO",
            filas_afectadas=1,
            detalle={
                "tarea_id": str(tarea_id),
                "estado_anterior": estado_anterior,
                "estado_nuevo": nuevo_estado,
            },
            ip=ip,
        )
        return TareaResponse.model_validate(tarea, from_attributes=True)

    # ------------------------------------------------------------------
    # 4.4 — Mis tareas
    # ------------------------------------------------------------------

    async def listar_mis_tareas(
        self,
        *,
        auth_user_id: uuid.UUID,
        estado: str | None = None,
        materia_id: uuid.UUID | None = None,
    ) -> list[TareaResponse]:
        usuario_id = await self._resolve_usuario(auth_user_id)
        tareas = await self._tarea_repo.list_mis_tareas(
            usuario_id, estado=estado, materia_id=materia_id
        )
        return [TareaResponse.model_validate(t, from_attributes=True) for t in tareas]

    # ------------------------------------------------------------------
    # 4.5 — Listar admin
    # ------------------------------------------------------------------

    async def listar_admin(
        self,
        *,
        asignado_a: uuid.UUID | None = None,
        asignado_por: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        estado: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TareaResponse]:
        tareas = await self._tarea_repo.list_admin(
            asignado_a=asignado_a,
            asignado_por=asignado_por,
            materia_id=materia_id,
            estado=estado,
            limit=limit,
            offset=offset,
        )
        return [TareaResponse.model_validate(t, from_attributes=True) for t in tareas]

    # ------------------------------------------------------------------
    # 4.6 — Agregar comentario
    # ------------------------------------------------------------------

    async def agregar_comentario(
        self,
        *,
        actor_auth_id: uuid.UUID,
        tarea_id: uuid.UUID,
        payload: CrearComentarioRequest,
        ip: str | None = None,
    ) -> ComentarioResponse:
        tarea = await self._tarea_repo.get(tarea_id)
        if tarea is None:
            raise TareaNotFoundError()
        actor_id = await self._resolve_usuario(actor_auth_id)
        from app.models.base import utc_now
        comentario = await self._comentario_repo.create(
            tarea_id=tarea_id,
            autor_id=actor_id,
            texto=payload.texto,
            comentado_at=utc_now(),
        )
        await audit_action(
            session=self.session,
            actor_id=actor_auth_id,
            tenant_id=self.tenant_id,
            accion="TAREA_COMENTAR",
            filas_afectadas=1,
            detalle={"tarea_id": str(tarea_id), "comentario_id": str(comentario.id)},
            ip=ip,
        )
        return ComentarioResponse.model_validate(comentario, from_attributes=True)

    # ------------------------------------------------------------------
    # 4.7 — Listar comentarios
    # ------------------------------------------------------------------

    async def listar_comentarios(self, *, tarea_id: uuid.UUID) -> list[ComentarioResponse]:
        tarea = await self._tarea_repo.get(tarea_id)
        if tarea is None:
            raise TareaNotFoundError()
        comentarios = await self._comentario_repo.list_by_tarea(tarea_id)
        return [ComentarioResponse.model_validate(c, from_attributes=True) for c in comentarios]
