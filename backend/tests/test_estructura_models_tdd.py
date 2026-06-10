"""TDD tests for estructura models — Carrera, Cohorte, Materia.

Covers:
- Unicidad (tenant_id, codigo) en Carrera enforceada por DB
- Unicidad (tenant_id, carrera_id, nombre) en Cohorte enforceada por DB
- Unicidad (tenant_id, codigo) en Materia enforceada por DB
- Estado por defecto "Activa" en las tres entidades
- Soft delete: deleted_at se establece, registro no desaparece de la DB
- Mismo código puede existir en tenants distintos (aislamiento)
- Cohorte con FK a Carrera correcta
"""
from __future__ import annotations

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, get_session_factory, initialize_database
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Tenant
from app.models.rbac import Permiso, Rol, RolPermiso
from app.models.estructura import Carrera, Cohorte, Materia


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def estructura_db_session(valid_env):
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
        await conn.run_sync(Carrera.__table__.create, checkfirst=True)
        await conn.run_sync(Cohorte.__table__.create, checkfirst=True)
        await conn.run_sync(Materia.__table__.create, checkfirst=True)

    session_factory = get_session_factory()

    async with session_factory() as session:
        # Clean FK order
        await session.execute(delete(Cohorte))
        await session.execute(delete(Carrera))
        await session.execute(delete(Materia))
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

        tenant_a = Tenant(name="Tenant Estructura A", slug="tenant-est-a")
        tenant_b = Tenant(name="Tenant Estructura B", slug="tenant-est-b")
        session.add_all([tenant_a, tenant_b])
        await session.commit()

        yield session, tenant_a, tenant_b

        await session.execute(delete(Cohorte))
        await session.execute(delete(Carrera))
        await session.execute(delete(Materia))
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


# ---------------------------------------------------------------------------
# Carrera
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_carrera_unicidad_codigo_en_mismo_tenant_enforceada_por_db(estructura_db_session):
    """Unicidad (tenant_id, codigo) en Carrera es enforceada por DB."""
    session, tenant_a, _ = estructura_db_session

    c1 = Carrera(tenant_id=tenant_a.id, codigo="TUPAD", nombre="Tecnicatura UP A Distancia")
    session.add(c1)
    await session.flush()

    c2 = Carrera(tenant_id=tenant_a.id, codigo="TUPAD", nombre="Duplicado")
    session.add(c2)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_carrera_mismo_codigo_en_tenants_distintos_coexiste(estructura_db_session):
    """El mismo código de carrera puede existir en tenants distintos."""
    session, tenant_a, tenant_b = estructura_db_session

    c_a = Carrera(tenant_id=tenant_a.id, codigo="TUPAD", nombre="Carrera A")
    c_b = Carrera(tenant_id=tenant_b.id, codigo="TUPAD", nombre="Carrera B")
    session.add_all([c_a, c_b])
    await session.commit()

    result = await session.scalars(select(Carrera).where(Carrera.codigo == "TUPAD"))
    carreras = list(result.all())
    assert len(carreras) == 2
    tenant_ids = {c.tenant_id for c in carreras}
    assert tenant_ids == {tenant_a.id, tenant_b.id}


@pytest.mark.asyncio
async def test_carrera_estado_activa_por_defecto(estructura_db_session):
    """Estado de Carrera es 'Activa' por defecto."""
    session, tenant_a, _ = estructura_db_session

    c = Carrera(tenant_id=tenant_a.id, codigo="ING", nombre="Ingeniería")
    session.add(c)
    await session.commit()

    persisted = await session.scalar(select(Carrera).where(Carrera.id == c.id))
    assert persisted is not None
    assert persisted.estado == "Activa"


@pytest.mark.asyncio
async def test_carrera_soft_delete_preserva_registro(estructura_db_session):
    """Soft delete: deleted_at se establece y el registro persiste en la DB."""
    from app.models.base import utc_now

    session, tenant_a, _ = estructura_db_session

    c = Carrera(tenant_id=tenant_a.id, codigo="LIC", nombre="Licenciatura")
    session.add(c)
    await session.commit()

    c.deleted_at = utc_now()
    await session.commit()

    persisted = await session.scalar(
        select(Carrera).where(Carrera.id == c.id)
    )
    assert persisted is not None
    assert persisted.deleted_at is not None


# ---------------------------------------------------------------------------
# Cohorte
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cohorte_unicidad_compuesta_enforceada_por_db(estructura_db_session):
    """Unicidad (tenant_id, carrera_id, nombre) en Cohorte enforceada por DB."""
    from datetime import date

    session, tenant_a, _ = estructura_db_session

    carrera = Carrera(tenant_id=tenant_a.id, codigo="TUPAD2", nombre="TUPAD")
    session.add(carrera)
    await session.flush()

    coh1 = Cohorte(
        tenant_id=tenant_a.id, carrera_id=carrera.id,
        nombre="MAR-2026", anio=2026,
        vig_desde=date(2026, 3, 1),
    )
    session.add(coh1)
    await session.flush()

    coh2 = Cohorte(
        tenant_id=tenant_a.id, carrera_id=carrera.id,
        nombre="MAR-2026", anio=2026,
        vig_desde=date(2026, 3, 1),
    )
    session.add(coh2)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_cohortes_iguales_en_distintas_carreras_del_mismo_tenant_coexisten(estructura_db_session):
    """Cohortes de igual nombre en distintas carreras del mismo tenant coexisten."""
    from datetime import date

    session, tenant_a, _ = estructura_db_session

    c1 = Carrera(tenant_id=tenant_a.id, codigo="CA1", nombre="Carrera 1")
    c2 = Carrera(tenant_id=tenant_a.id, codigo="CA2", nombre="Carrera 2")
    session.add_all([c1, c2])
    await session.flush()

    coh1 = Cohorte(tenant_id=tenant_a.id, carrera_id=c1.id, nombre="AGO-2025", anio=2025, vig_desde=date(2025, 8, 1))
    coh2 = Cohorte(tenant_id=tenant_a.id, carrera_id=c2.id, nombre="AGO-2025", anio=2025, vig_desde=date(2025, 8, 1))
    session.add_all([coh1, coh2])
    await session.commit()

    result = await session.scalars(select(Cohorte).where(Cohorte.nombre == "AGO-2025"))
    cohortes = list(result.all())
    assert len(cohortes) == 2
    carrera_ids = {co.carrera_id for co in cohortes}
    assert carrera_ids == {c1.id, c2.id}


@pytest.mark.asyncio
async def test_cohorte_estado_activa_por_defecto(estructura_db_session):
    """Estado de Cohorte es 'Activa' por defecto."""
    from datetime import date

    session, tenant_a, _ = estructura_db_session

    carrera = Carrera(tenant_id=tenant_a.id, codigo="DEF", nombre="Defecto")
    session.add(carrera)
    await session.flush()

    coh = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera.id, nombre="JUN-2026", anio=2026, vig_desde=date(2026, 6, 1))
    session.add(coh)
    await session.commit()

    persisted = await session.scalar(select(Cohorte).where(Cohorte.id == coh.id))
    assert persisted is not None
    assert persisted.estado == "Activa"


# ---------------------------------------------------------------------------
# Materia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_materia_unicidad_codigo_en_mismo_tenant_enforceada_por_db(estructura_db_session):
    """Unicidad (tenant_id, codigo) en Materia enforceada por DB."""
    session, tenant_a, _ = estructura_db_session

    m1 = Materia(tenant_id=tenant_a.id, codigo="PROG_I", nombre="Programación I")
    session.add(m1)
    await session.flush()

    m2 = Materia(tenant_id=tenant_a.id, codigo="PROG_I", nombre="Duplicado")
    session.add(m2)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_materia_mismo_codigo_en_tenants_distintos_coexiste(estructura_db_session):
    """El mismo código de materia puede existir en tenants distintos."""
    session, tenant_a, tenant_b = estructura_db_session

    m_a = Materia(tenant_id=tenant_a.id, codigo="BD", nombre="Bases de Datos A")
    m_b = Materia(tenant_id=tenant_b.id, codigo="BD", nombre="Bases de Datos B")
    session.add_all([m_a, m_b])
    await session.commit()

    result = await session.scalars(select(Materia).where(Materia.codigo == "BD"))
    materias = list(result.all())
    assert len(materias) == 2


@pytest.mark.asyncio
async def test_materia_estado_activa_por_defecto(estructura_db_session):
    """Estado de Materia es 'Activa' por defecto."""
    session, tenant_a, _ = estructura_db_session

    m = Materia(tenant_id=tenant_a.id, codigo="SO", nombre="Sistemas Operativos")
    session.add(m)
    await session.commit()

    persisted = await session.scalar(select(Materia).where(Materia.id == m.id))
    assert persisted is not None
    assert persisted.estado == "Activa"


@pytest.mark.asyncio
async def test_materia_soft_delete_preserva_registro(estructura_db_session):
    """Soft delete en Materia: deleted_at se establece y el registro persiste."""
    from app.models.base import utc_now

    session, tenant_a, _ = estructura_db_session

    m = Materia(tenant_id=tenant_a.id, codigo="REDES", nombre="Redes")
    session.add(m)
    await session.commit()

    m.deleted_at = utc_now()
    await session.commit()

    persisted = await session.scalar(select(Materia).where(Materia.id == m.id))
    assert persisted is not None
    assert persisted.deleted_at is not None
