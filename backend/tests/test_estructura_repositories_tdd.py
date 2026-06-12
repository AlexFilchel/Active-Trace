"""TDD tests for estructura repositories — Carrera, Cohorte, Materia.

Covers:
- list devuelve solo registros del tenant del usuario autenticado
- get por ID de otro tenant devuelve None (aislamiento)
- get_by_codigo solo ve el código dentro del tenant correcto
- list excluye soft-deleted por defecto
- CohorteRepository soporta filtro por carrera_id
- MateriaRepository soporta filtro por estado
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import delete

from app.core.database import get_session_factory, initialize_database
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Tenant
from app.models.rbac import Permiso, Rol, RolPermiso
from app.models.estructura import Carrera, Cohorte, Materia
from app.models.usuarios import Asignacion, Usuario
from app.repositories.estructura import CarreraRepository, CohorteRepository, MateriaRepository


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def repo_db_session(valid_env):
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
        await session.execute(delete(Asignacion))
        await session.execute(delete(Cohorte))
        await session.execute(delete(Carrera))
        await session.execute(delete(Materia))
        await session.execute(delete(RolPermiso))
        await session.execute(delete(Permiso))
        await session.execute(delete(Rol))
        await session.execute(delete(Usuario))
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

        tenant_a = Tenant(name="Repo Tenant A", slug="repo-a")
        tenant_b = Tenant(name="Repo Tenant B", slug="repo-b")
        session.add_all([tenant_a, tenant_b])
        await session.commit()

        yield session, tenant_a, tenant_b

        await session.execute(delete(Asignacion))
        await session.execute(delete(Cohorte))
        await session.execute(delete(Carrera))
        await session.execute(delete(Materia))
        await session.execute(delete(RolPermiso))
        await session.execute(delete(Permiso))
        await session.execute(delete(Rol))
        await session.execute(delete(Usuario))
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()


# ---------------------------------------------------------------------------
# CarreraRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_carrera_repo_list_devuelve_solo_del_tenant_correcto(repo_db_session):
    """list() devuelve solo registros del tenant del repositorio."""
    session, tenant_a, tenant_b = repo_db_session

    c_a = Carrera(tenant_id=tenant_a.id, codigo="A1", nombre="Carrera A1")
    c_b = Carrera(tenant_id=tenant_b.id, codigo="B1", nombre="Carrera B1")
    session.add_all([c_a, c_b])
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tenant_a.id)
    carreras = await repo.list()

    assert len(carreras) == 1
    assert carreras[0].codigo == "A1"


@pytest.mark.asyncio
async def test_carrera_repo_get_de_otro_tenant_devuelve_none(repo_db_session):
    """get() de una entidad de otro tenant devuelve None."""
    session, tenant_a, tenant_b = repo_db_session

    c_b = Carrera(tenant_id=tenant_b.id, codigo="B2", nombre="Carrera B2")
    session.add(c_b)
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tenant_a.id)
    result = await repo.get(c_b.id)

    assert result is None


@pytest.mark.asyncio
async def test_carrera_repo_get_by_codigo_dentro_del_tenant(repo_db_session):
    """get_by_codigo() devuelve la carrera correcta dentro del tenant."""
    session, tenant_a, tenant_b = repo_db_session

    c_a = Carrera(tenant_id=tenant_a.id, codigo="MATCH", nombre="Match A")
    c_b = Carrera(tenant_id=tenant_b.id, codigo="MATCH", nombre="Match B")
    session.add_all([c_a, c_b])
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tenant_a.id)
    result = await repo.get_by_codigo("MATCH")

    assert result is not None
    assert result.tenant_id == tenant_a.id


@pytest.mark.asyncio
async def test_carrera_repo_list_excluye_soft_deleted(repo_db_session):
    """list() excluye registros con deleted_at establecido."""
    from app.models.base import utc_now

    session, tenant_a, _ = repo_db_session

    c_active = Carrera(tenant_id=tenant_a.id, codigo="ACT", nombre="Activa")
    c_deleted = Carrera(tenant_id=tenant_a.id, codigo="DEL", nombre="Borrada", deleted_at=utc_now())
    session.add_all([c_active, c_deleted])
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tenant_a.id)
    carreras = await repo.list()

    assert len(carreras) == 1
    assert carreras[0].codigo == "ACT"


# ---------------------------------------------------------------------------
# CohorteRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cohorte_repo_list_devuelve_solo_del_tenant(repo_db_session):
    """CohorteRepository.list() filtra por tenant."""
    session, tenant_a, tenant_b = repo_db_session

    c_a = Carrera(tenant_id=tenant_a.id, codigo="CRA", nombre="Carrera A")
    c_b = Carrera(tenant_id=tenant_b.id, codigo="CRB", nombre="Carrera B")
    session.add_all([c_a, c_b])
    await session.flush()

    coh_a = Cohorte(tenant_id=tenant_a.id, carrera_id=c_a.id, nombre="MAR-2026", anio=2026, vig_desde=date(2026, 3, 1))
    coh_b = Cohorte(tenant_id=tenant_b.id, carrera_id=c_b.id, nombre="MAR-2026", anio=2026, vig_desde=date(2026, 3, 1))
    session.add_all([coh_a, coh_b])
    await session.commit()

    repo = CohorteRepository(session=session, tenant_id=tenant_a.id)
    cohortes = await repo.list()

    assert len(cohortes) == 1
    assert cohortes[0].tenant_id == tenant_a.id


@pytest.mark.asyncio
async def test_cohorte_repo_list_por_carrera_id(repo_db_session):
    """CohorteRepository.list_by_carrera() filtra por carrera_id."""
    session, tenant_a, _ = repo_db_session

    c1 = Carrera(tenant_id=tenant_a.id, codigo="CX1", nombre="Carrera X1")
    c2 = Carrera(tenant_id=tenant_a.id, codigo="CX2", nombre="Carrera X2")
    session.add_all([c1, c2])
    await session.flush()

    coh1 = Cohorte(tenant_id=tenant_a.id, carrera_id=c1.id, nombre="AGO-2025", anio=2025, vig_desde=date(2025, 8, 1))
    coh2 = Cohorte(tenant_id=tenant_a.id, carrera_id=c2.id, nombre="AGO-2025", anio=2025, vig_desde=date(2025, 8, 1))
    session.add_all([coh1, coh2])
    await session.commit()

    repo = CohorteRepository(session=session, tenant_id=tenant_a.id)
    resultado = await repo.list_by_carrera(c1.id)

    assert len(resultado) == 1
    assert resultado[0].carrera_id == c1.id


@pytest.mark.asyncio
async def test_cohorte_repo_get_de_otro_tenant_devuelve_none(repo_db_session):
    """CohorteRepository.get() de otro tenant devuelve None."""
    session, tenant_a, tenant_b = repo_db_session

    c_b = Carrera(tenant_id=tenant_b.id, codigo="CB3", nombre="Carrera B3")
    session.add(c_b)
    await session.flush()

    coh_b = Cohorte(tenant_id=tenant_b.id, carrera_id=c_b.id, nombre="X-2026", anio=2026, vig_desde=date(2026, 1, 1))
    session.add(coh_b)
    await session.commit()

    repo = CohorteRepository(session=session, tenant_id=tenant_a.id)
    result = await repo.get(coh_b.id)

    assert result is None


# ---------------------------------------------------------------------------
# MateriaRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_materia_repo_list_devuelve_solo_del_tenant(repo_db_session):
    """MateriaRepository.list() filtra por tenant."""
    session, tenant_a, tenant_b = repo_db_session

    m_a = Materia(tenant_id=tenant_a.id, codigo="MA1", nombre="Materia A1")
    m_b = Materia(tenant_id=tenant_b.id, codigo="MB1", nombre="Materia B1")
    session.add_all([m_a, m_b])
    await session.commit()

    repo = MateriaRepository(session=session, tenant_id=tenant_a.id)
    materias = await repo.list()

    assert len(materias) == 1
    assert materias[0].codigo == "MA1"


@pytest.mark.asyncio
async def test_materia_repo_list_por_estado(repo_db_session):
    """MateriaRepository.list_by_estado() filtra por estado."""
    session, tenant_a, _ = repo_db_session

    m_act = Materia(tenant_id=tenant_a.id, codigo="MA2", nombre="Activa", estado="Activa")
    m_ina = Materia(tenant_id=tenant_a.id, codigo="MA3", nombre="Inactiva", estado="Inactiva")
    session.add_all([m_act, m_ina])
    await session.commit()

    repo = MateriaRepository(session=session, tenant_id=tenant_a.id)
    activas = await repo.list_by_estado("Activa")

    assert len(activas) == 1
    assert activas[0].codigo == "MA2"


@pytest.mark.asyncio
async def test_materia_repo_get_de_otro_tenant_devuelve_none(repo_db_session):
    """MateriaRepository.get() de otro tenant devuelve None."""
    session, tenant_a, tenant_b = repo_db_session

    m_b = Materia(tenant_id=tenant_b.id, codigo="MB2", nombre="Materia B2")
    session.add(m_b)
    await session.commit()

    repo = MateriaRepository(session=session, tenant_id=tenant_a.id)
    result = await repo.get(m_b.id)

    assert result is None
