from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.permissions import get_user_permissions
from app.models import AuthUser, Permiso, Rol, RolPermiso, Usuario
from tests.usuarios_test_utils import tenant_session


@pytest.fixture
async def rbac_assignment_session(valid_env):
    async for item in tenant_session():
        yield item


@pytest.mark.asyncio
async def test_vencida_assignment_does_not_grant_effective_permissions(rbac_assignment_session):
    session, tenant_a, _ = rbac_assignment_session
    from app.models import Asignacion

    auth_user = AuthUser(tenant_id=tenant_a.id, email="coord@test.local", password_hash="hash", roles=[])
    rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
    permiso = Permiso(tenant_id=tenant_a.id, nombre="equipos:asignar")
    session.add_all([auth_user, rol, permiso])
    await session.flush()
    session.add(RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=permiso.id))
    usuario = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_user.id, nombre="Coord", apellidos="User", email_encrypted="enc", email_hash="hash")
    session.add(usuario)
    await session.flush()
    session.add(
        Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario.id,
            rol_id=rol.id,
            desde=date.today() - timedelta(days=10),
            hasta=date.today() - timedelta(days=1),
        )
    )
    await session.commit()

    assert await get_user_permissions([], tenant_a.id, session, auth_user_id=auth_user.id) == set()


@pytest.mark.asyncio
async def test_active_multi_role_assignments_union_permissions_without_duplicates(rbac_assignment_session):
    session, tenant_a, _ = rbac_assignment_session
    from app.models import Asignacion

    auth_user = AuthUser(tenant_id=tenant_a.id, email="multi@test.local", password_hash="hash", roles=[])
    rol_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
    rol_b = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
    permiso_a = Permiso(tenant_id=tenant_a.id, nombre="equipos:asignar")
    permiso_b = Permiso(tenant_id=tenant_a.id, nombre="usuarios:gestionar")
    permiso_overlap = Permiso(tenant_id=tenant_a.id, nombre="avisos:confirmar")
    session.add_all([auth_user, rol_a, rol_b, permiso_a, permiso_b, permiso_overlap])
    await session.flush()
    session.add_all(
        [
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_a.id, permiso_id=permiso_a.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_a.id, permiso_id=permiso_overlap.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_b.id, permiso_id=permiso_b.id),
            RolPermiso(tenant_id=tenant_a.id, rol_id=rol_b.id, permiso_id=permiso_overlap.id),
        ]
    )
    usuario = Usuario(tenant_id=tenant_a.id, auth_user_id=auth_user.id, nombre="Multi", apellidos="Role", email_encrypted="enc", email_hash="hash")
    session.add(usuario)
    await session.flush()
    session.add_all(
        [
            Asignacion(tenant_id=tenant_a.id, usuario_id=usuario.id, rol_id=rol_a.id, desde=date.today() - timedelta(days=1)),
            Asignacion(tenant_id=tenant_a.id, usuario_id=usuario.id, rol_id=rol_b.id, desde=date.today() - timedelta(days=1)),
        ]
    )
    await session.commit()

    permissions = await get_user_permissions([], tenant_a.id, session, auth_user_id=auth_user.id)
    assert permissions == {"equipos:asignar", "usuarios:gestionar", "avisos:confirmar"}
