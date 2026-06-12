from __future__ import annotations

from datetime import date
import uuid

from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuarios import Asignacion, Usuario
from app.repositories.tenant_scoped import TenantScopedRepository


class UsuarioRepository(TenantScopedRepository[Usuario]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=Usuario, tenant_id=tenant_id)

    async def get_by_email_hash(self, email_hash: str) -> Usuario | None:
        statement = self._base_query().where(Usuario.email_hash == email_hash)
        return await self.session.scalar(statement)

    async def get_by_auth_user_id(self, auth_user_id: uuid.UUID) -> Usuario | None:
        statement = self._base_query().where(Usuario.auth_user_id == auth_user_id)
        return await self.session.scalar(statement)

    async def search_docentes(self, q: str, *, limit: int = 20) -> list[Usuario]:
        from sqlalchemy import select
        stmt = (
            select(Usuario)
            .where(Usuario.tenant_id == self.context.tenant_id)
            .where(Usuario.deleted_at.is_(None))
            .where(Usuario.estado == "Activo")
            .where(
                or_(
                    Usuario.nombre.ilike(f"%{q}%"),
                    Usuario.apellidos.ilike(f"%{q}%"),
                )
            )
            .order_by(Usuario.apellidos, Usuario.nombre)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())


class AsignacionRepository(TenantScopedRepository[Asignacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=Asignacion, tenant_id=tenant_id)

    async def list(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        rol_id: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        active_only: bool = False,
        on_date: date | None = None,
    ) -> list[Asignacion]:
        statement = self._base_query(include_deleted=include_deleted)
        if usuario_id is not None:
            statement = statement.where(Asignacion.usuario_id == usuario_id)
        if rol_id is not None:
            statement = statement.where(Asignacion.rol_id == rol_id)
        if materia_id is not None:
            statement = statement.where(Asignacion.materia_id == materia_id)
        if carrera_id is not None:
            statement = statement.where(Asignacion.carrera_id == carrera_id)
        if cohorte_id is not None:
            statement = statement.where(Asignacion.cohorte_id == cohorte_id)
        if active_only:
            today = on_date or date.today()
            statement = statement.where(Asignacion.desde <= today).where((Asignacion.hasta.is_(None)) | (Asignacion.hasta >= today))
        result = await self.session.scalars(statement.order_by(Asignacion.desde.desc(), Asignacion.created_at.asc()))
        return list(result.all())

    async def list_vigentes_for_user(self, usuario_id: uuid.UUID, *, on_date: date | None = None) -> list[Asignacion]:
        return await self.list(usuario_id=usuario_id, active_only=True, on_date=on_date)

    async def get_by_usuario_and_rol(self, usuario_id: uuid.UUID, rol_id: uuid.UUID) -> list[Asignacion]:
        return await self.list(usuario_id=usuario_id, rol_id=rol_id)

    async def get_by_usuario(self, usuario_id: uuid.UUID) -> list[Asignacion]:
        return await self.list(usuario_id=usuario_id)

    async def list_by_equipo(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        rol_id: uuid.UUID | None = None,
        usuario_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[Asignacion]:
        return await self.list(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            rol_id=rol_id,
            usuario_id=usuario_id,
            active_only=active_only,
        )

    async def bulk_create(self, asignaciones: list[Asignacion]) -> list[Asignacion]:
        self.session.add_all(asignaciones)
        await self.session.flush()
        return asignaciones

    async def bulk_update_vigencia(
        self,
        *,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        desde: date,
        hasta: date | None,
    ) -> int:
        stmt = (
            update(Asignacion)
            .where(Asignacion.tenant_id == self.context.tenant_id)
            .where(Asignacion.materia_id == materia_id)
            .where(Asignacion.carrera_id == carrera_id)
            .where(Asignacion.cohorte_id == cohorte_id)
            .where(Asignacion.deleted_at.is_(None))
            .values(desde=desde, hasta=hasta)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_vigentes_by_equipo(
        self,
        *,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[Asignacion]:
        return await self.list(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            active_only=True,
        )
