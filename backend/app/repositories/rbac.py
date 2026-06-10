"""RBAC repository — resolución de permisos efectivos por rol y tenant."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permiso, Rol, RolPermiso
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
