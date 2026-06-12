"""RBAC repository — resolución de permisos efectivos por rol y tenant."""
from __future__ import annotations

from datetime import date
import uuid

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permiso, Rol, RolPermiso
from app.models.usuarios import Asignacion, Usuario
from app.repositories.tenant_scoped import TenantScopedRepository


class RbacRepository(TenantScopedRepository[Rol]):
    """Repository para el catálogo RBAC (Rol, Permiso, RolPermiso).

    Hereda TenantScopedRepository[Rol] para operaciones CRUD sobre roles.
    Agrega el método especializado para resolución de permisos efectivos.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str) -> None:
        super().__init__(session=session, model=Rol, tenant_id=tenant_id)

    async def get_permissions_for_roles(self, role_names: list[str]) -> set[str]:
        """Resuelve la unión de permisos efectivos para la lista de roles dados.

        Ejecuta un JOIN Rol → RolPermiso → Permiso filtrando por tenant y
        soft delete. Retorna un set vacío si role_names está vacío o si ningún
        rol existe en el tenant.

        Args:
            role_names: Lista de nombres de rol (del JWT claim ``roles``).

        Returns:
            Conjunto de strings ``modulo:accion`` de permisos efectivos.
        """
        if not role_names:
            return set()

        statement = (
            select(Permiso.nombre)
            .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
            .join(Rol, Rol.id == RolPermiso.rol_id)
            .where(
                Rol.nombre.in_(role_names),
                RolPermiso.tenant_id == self.context.tenant_id,
                RolPermiso.deleted_at.is_(None),
                Rol.tenant_id == self.context.tenant_id,
                Rol.deleted_at.is_(None),
                Permiso.tenant_id == self.context.tenant_id,
                Permiso.deleted_at.is_(None),
            )
        )

        result = await self.session.scalars(statement)
        return set(result.all())

    async def get_rol_by_name(self, nombre: str) -> Rol | None:
        """Retorna un Rol activo por nombre dentro del tenant actual."""
        statement = self._base_query().where(Rol.nombre == nombre)
        return await self.session.scalar(statement)

    async def get_active_assignment_permissions_for_auth_user(
        self,
        *,
        auth_user_id: uuid.UUID,
        on_date: date | None = None,
    ) -> set[str]:
        today = on_date or date.today()
        connection = await self.session.connection()

        def _has_assignment_tables(sync_connection) -> bool:
            inspector = inspect(sync_connection)
            return inspector.has_table("usuario") and inspector.has_table("asignacion")

        if not await connection.run_sync(_has_assignment_tables):
            return set()

        statement = (
            select(Permiso.nombre)
            .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
            .join(Rol, Rol.id == RolPermiso.rol_id)
            .join(Asignacion, Asignacion.rol_id == Rol.id)
            .join(Usuario, Usuario.id == Asignacion.usuario_id)
            .where(
                Usuario.auth_user_id == auth_user_id,
                Usuario.tenant_id == self.context.tenant_id,
                Usuario.deleted_at.is_(None),
                Asignacion.tenant_id == self.context.tenant_id,
                Asignacion.deleted_at.is_(None),
                Asignacion.desde <= today,
                (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= today),
                RolPermiso.tenant_id == self.context.tenant_id,
                RolPermiso.deleted_at.is_(None),
                Rol.tenant_id == self.context.tenant_id,
                Rol.deleted_at.is_(None),
                Permiso.tenant_id == self.context.tenant_id,
                Permiso.deleted_at.is_(None),
            )
        )
        result = await self.session.scalars(statement)
        return set(result.all())
