"""TDD tests for RBAC models — Rol, Permiso, RolPermiso.

Covers:
- Unicidad (tenant_id, nombre) en Rol enforceada por DB
- Unicidad (tenant_id, nombre) en Permiso enforceada por DB
- El mismo nombre de rol puede existir en tenants distintos
- Unicidad (rol_id, permiso_id) en RolPermiso enforceada por DB
"""
from __future__ import annotations

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, get_session_factory, initialize_database
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Tenant
from app.models.rbac import Permiso, Rol, RolPermiso


@pytest.fixture
async def rbac_db_session(valid_env):
    engine = initialize_database()

    async with engine.begin() as connection:
        await connection.run_sync(Tenant.__table__.create, checkfirst=True)
        await connection.run_sync(AuthUser.__table__.create, checkfirst=True)
        await connection.run_sync(AuthRefreshSession.__table__.create, checkfirst=True)
        await connection.run_sync(AuthTotpCredential.__table__.create, checkfirst=True)
        await connection.run_sync(AuthLoginChallenge.__table__.create, checkfirst=True)
        await connection.run_sync(AuthPasswordResetToken.__table__.create, checkfirst=True)
        await connection.run_sync(Rol.__table__.create, checkfirst=True)
        await connection.run_sync(Permiso.__table__.create, checkfirst=True)
        await connection.run_sync(RolPermiso.__table__.create, checkfirst=True)

    session_factory = get_session_factory()

    async with session_factory() as session:
        # Clean up any prior data — order respects FK constraints
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

        tenant_a = Tenant(name="Tenant RBAC A", slug="tenant-rbac-a")
        tenant_b = Tenant(name="Tenant RBAC B", slug="tenant-rbac-b")
        session.add_all([tenant_a, tenant_b])
        await session.commit()

        yield session, tenant_a, tenant_b

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


@pytest.mark.asyncio
async def test_rol_unicidad_en_mismo_tenant_es_enforceada_por_db(rbac_db_session):
    """Unicidad (tenant_id, nombre) en Rol es enforceada por DB."""
    session, tenant_a, _tenant_b = rbac_db_session

    rol1 = Rol(tenant_id=tenant_a.id, nombre="PROFESOR", descripcion="Docente")
    session.add(rol1)
    await session.flush()

    rol2 = Rol(tenant_id=tenant_a.id, nombre="PROFESOR", descripcion="Duplicado")
    session.add(rol2)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_mismo_nombre_de_rol_existe_en_tenants_distintos_sin_conflicto(rbac_db_session):
    """El mismo nombre de rol puede existir en tenants distintos."""
    session, tenant_a, tenant_b = rbac_db_session

    rol_a = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
    rol_b = Rol(tenant_id=tenant_b.id, nombre="PROFESOR")
    session.add_all([rol_a, rol_b])
    await session.commit()

    # Both should exist
    result = await session.scalars(select(Rol).where(Rol.nombre == "PROFESOR"))
    roles = list(result.all())
    assert len(roles) == 2
    tenant_ids = {r.tenant_id for r in roles}
    assert tenant_ids == {tenant_a.id, tenant_b.id}


@pytest.mark.asyncio
async def test_permiso_unicidad_en_mismo_tenant_es_enforceada_por_db(rbac_db_session):
    """Unicidad (tenant_id, nombre) en Permiso es enforceada por DB."""
    session, tenant_a, _tenant_b = rbac_db_session

    p1 = Permiso(tenant_id=tenant_a.id, nombre="calificaciones:importar")
    session.add(p1)
    await session.flush()

    p2 = Permiso(tenant_id=tenant_a.id, nombre="calificaciones:importar")
    session.add(p2)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_permiso_formato_modulo_accion_persiste_correctamente(rbac_db_session):
    """Permiso con nombre modulo:accion se persiste correctamente."""
    session, tenant_a, _tenant_b = rbac_db_session

    p = Permiso(tenant_id=tenant_a.id, nombre="equipos:asignar")
    session.add(p)
    await session.commit()

    persisted = await session.scalar(select(Permiso).where(Permiso.id == p.id))
    assert persisted is not None
    assert persisted.nombre == "equipos:asignar"
    assert persisted.tenant_id == tenant_a.id


@pytest.mark.asyncio
async def test_rol_permiso_unicidad_enforceada_por_db(rbac_db_session):
    """Unicidad (rol_id, permiso_id) en RolPermiso es enforceada por DB."""
    session, tenant_a, _tenant_b = rbac_db_session

    rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
    permiso = Permiso(tenant_id=tenant_a.id, nombre="equipos:asignar")
    session.add_all([rol, permiso])
    await session.flush()

    rp1 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=permiso.id)
    session.add(rp1)
    await session.flush()

    rp2 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=permiso.id)
    session.add(rp2)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_rol_puede_tener_multiples_permisos(rbac_db_session):
    """Un rol puede tener múltiples permisos asignados."""
    session, tenant_a, _tenant_b = rbac_db_session

    rol = Rol(tenant_id=tenant_a.id, nombre="ADMIN")
    p1 = Permiso(tenant_id=tenant_a.id, nombre="auditoria:ver")
    p2 = Permiso(tenant_id=tenant_a.id, nombre="usuarios:gestionar")
    p3 = Permiso(tenant_id=tenant_a.id, nombre="estructura:gestionar")
    session.add_all([rol, p1, p2, p3])
    await session.flush()

    rp1 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=p1.id)
    rp2 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=p2.id)
    rp3 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=p3.id)
    session.add_all([rp1, rp2, rp3])
    await session.commit()

    result = await session.scalars(select(RolPermiso).where(RolPermiso.rol_id == rol.id))
    associations = list(result.all())
    assert len(associations) == 3
