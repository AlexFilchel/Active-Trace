"""RBAC permission resolution and FastAPI guards.

Exports:
    get_user_permissions — resolves effective permission set for a list of role names.
    require_permission   — FastAPI Depends factory; raises 403 if permission missing.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.repositories.rbac import RbacRepository


async def get_user_permissions(
    roles: list[str],
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> set[str]:
    """Resolve the union of effective permissions for the given roles within a tenant.

    Queries the DB (Rol → RolPermiso → Permiso) and returns a set of
    ``modulo:accion`` strings. Returns an empty set if ``roles`` is empty or
    no matching roles exist in the tenant.

    Args:
        roles:     List of role name strings (from JWT claim ``roles``).
        tenant_id: Tenant scope for the resolution.
        session:   Active async database session.

    Returns:
        Set of permission strings for the given roles in the tenant.
    """
    repo = RbacRepository(session=session, tenant_id=tenant_id)
    return await repo.get_permissions_for_roles(roles)


def require_permission(permission: str) -> Depends:
    """Return a FastAPI ``Depends`` that enforces the given permission.

    Usage in a router::

        @router.get("/calificaciones", dependencies=[require_permission("calificaciones:importar")])
        async def list_calificaciones(): ...

    Or to access the authenticated user inside the handler::

        async def endpoint(user: AuthenticatedUser = require_permission("calificaciones:importar")):
            ...

    Raises:
        HTTP 401 — if the request is not authenticated (delegated to ``get_current_user``).
        HTTP 403 — if the authenticated user does not hold ``permission`` (fail-closed).
    """

    async def _guard(
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedUser:
        effective_permissions = await get_user_permissions(
            current_user.roles,
            current_user.tenant_id,
            db,
        )

        if permission not in effective_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return current_user

    return Depends(_guard)
