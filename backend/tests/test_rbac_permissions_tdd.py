"""TDD tests for RBAC permission resolution (get_user_permissions).

Covers:
- Usuario con un rol resuelve sus permisos correctamente
- Usuario con múltiples roles recibe la unión de permisos (sin duplicados)
- Usuario sin roles tiene conjunto de permisos vacío
- Permisos de tenant A no se filtran en tenant B (aislamiento multi-tenant)
"""
from __future__ import annotations

import pytest
from sqlalchemy import delete

from app.core.database import get_session_factory, initialize_database
from app.core.permissions import get_user_permissions
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Permiso, Rol, RolPermiso, Tenant


@pytest.fixture
async def permissions_db_session(valid_env):
    engine = initialize_database()

    async with engine.begin() as conn:
        await conn.run_sync(Tenant.__table__.create, checkfirst=True)
        await conn.run_sync(AuthUser.__table__.create, checkfirst=True)
        await conn.run_sync(AuthRefreshSession.__table__.create, checkfirst=True)
        await conn.run_sync(AuthTotpCredential.__table__.create, checkfirst=True)
        await conn.run_sync(AuthLoginChallenge.__table__.create, checkfirst=True)
        await conn.run_sync(AuthPasswordResetToken.__table__.create, checkfirst=True)
        await conn.run_sync(Rol.__table__.create, checkfirst=True)
        await conn.run_sync(Permiso.__table__.create, checkfirst=True)
        await conn.run_sync(RolPermiso.__table__.create, checkfirst=True)

    session_factory = get_session_factory()

    async with session_factory() as session:
        # Clean up in FK order
        await session.execute(delete(RolPermiso))
        await session.execute(delete(Permiso))
        await session.execute(delete(Rol))
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

        tenant_a = Tenant(name="Permissions Tenant A", slug="perms-tenant-a")
        tenant_b = Tenant(name="Permissions Tenant B", slug="perms-tenant-b")
        session.add_all([tenant_a, tenant_b])
        await session.commit()

        # Tenant A roles and permissions
        rol_profesor_a = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        rol_coordinador_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        session.add_all([rol_profesor_a, rol_coordinador_a])
        await session.flush()

        p_importar = Permiso(tenant_id=tenant_a.id, nombre="calificaciones:importar")
        p_comunicar = Permiso(tenant_id=tenant_a.id, nombre="comunicacion:enviar")
        p_equipos = Permiso(tenant_id=tenant_a.id, nombre="equipos:gestionar")
        session.add_all([p_importar, p_comunicar, p_equipos])
        await session.flush()

        # PROFESOR gets: calificaciones:importar, comunicacion:enviar
        rp1 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_profesor_a.id, permiso_id=p_importar.id)
        rp2 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_profesor_a.id, permiso_id=p_comunicar.id)
        # COORDINADOR gets: comunicacion:enviar (overlap), equipos:gestionar
        rp3 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coordinador_a.id, permiso_id=p_comunicar.id)
        rp4 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coordinador_a.id, permiso_id=p_equipos.id)
        session.add_all([rp1, rp2, rp3, rp4])
        await session.commit()

        # Tenant B — different rol/permiso set
        rol_admin_b = Rol(tenant_id=tenant_b.id, nombre="ADMIN")
        session.add(rol_admin_b)
        await session.flush()
        p_admin_b = Permiso(tenant_id=tenant_b.id, nombre="tenant:configurar")
        session.add(p_admin_b)
        await session.flush()
        rp_b = RolPermiso(tenant_id=tenant_b.id, rol_id=rol_admin_b.id, permiso_id=p_admin_b.id)
        session.add(rp_b)
        await session.commit()

        yield session, tenant_a, tenant_b


@pytest.mark.asyncio
async def test_usuario_con_un_rol_resuelve_sus_permisos(permissions_db_session):
    """Usuario con rol PROFESOR resuelve exactamente sus permisos asignados."""
    session, tenant_a, _tenant_b = permissions_db_session

    permisos = await get_user_permissions(["PROFESOR"], tenant_a.id, session)

    assert permisos == {"calificaciones:importar", "comunicacion:enviar"}


@pytest.mark.asyncio
async def test_usuario_con_multiples_roles_recibe_union_sin_duplicados(permissions_db_session):
    """Usuario con PROFESOR + COORDINADOR recibe la unión de permisos (sin duplicados)."""
    session, tenant_a, _tenant_b = permissions_db_session

    permisos = await get_user_permissions(["PROFESOR", "COORDINADOR"], tenant_a.id, session)

    assert permisos == {"calificaciones:importar", "comunicacion:enviar", "equipos:gestionar"}
    # comunicacion:enviar is in both roles but appears once
    assert len(permisos) == 3


@pytest.mark.asyncio
async def test_usuario_sin_roles_tiene_permisos_vacios(permissions_db_session):
    """Usuario con roles=[] tiene conjunto de permisos vacío."""
    session, tenant_a, _tenant_b = permissions_db_session

    permisos = await get_user_permissions([], tenant_a.id, session)

    assert permisos == set()


@pytest.mark.asyncio
async def test_permisos_de_tenant_a_no_se_filtran_en_tenant_b(permissions_db_session):
    """Los roles de tenant A no otorgan permisos en tenant B."""
    session, tenant_a, tenant_b = permissions_db_session

    # PROFESOR exists in tenant A but NOT in tenant B
    permisos_b = await get_user_permissions(["PROFESOR"], tenant_b.id, session)

    assert permisos_b == set()

    # ADMIN exists in tenant B — its permissions should be from tenant B only
    permisos_admin_b = await get_user_permissions(["ADMIN"], tenant_b.id, session)
    assert permisos_admin_b == {"tenant:configurar"}

    # Same rol name ADMIN queried against tenant A returns empty (no ADMIN in tenant A fixture)
    permisos_admin_a = await get_user_permissions(["ADMIN"], tenant_a.id, session)
    assert permisos_admin_a == set()
