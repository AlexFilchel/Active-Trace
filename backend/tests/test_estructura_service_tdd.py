"""TDD tests para EstructuraService.

Covers:
- crear_carrera crea y devuelve la entidad
- crear_carrera con código duplicado lanza ConflictError (409)
- actualizar_carrera cambia el estado Activa → Inactiva
- obtener_carrera de otro tenant lanza NotFoundError (404)
- crear_cohorte en carrera Inactiva lanza BusinessRuleError (422)
- crear_cohorte en carrera Activa funciona
- inactivar carrera no afecta cohortes existentes
- crear_materia con código duplicado lanza ConflictError
- obtener_materia de otro tenant lanza NotFoundError
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
from app.services.estructura import EstructuraService, ConflictError, NotFoundError, BusinessRuleError


@pytest.fixture
async def svc_session(valid_env):
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

        tenant_a = Tenant(name="Svc Tenant A", slug="svc-a")
        tenant_b = Tenant(name="Svc Tenant B", slug="svc-b")
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
# Carrera
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_carrera_devuelve_entidad_persistida(svc_session):
    """crear_carrera() crea y devuelve la carrera con los datos correctos."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    carrera = await svc.crear_carrera(codigo="TUPAD", nombre="Tecnicatura UP A Distancia")

    assert carrera.id is not None
    assert carrera.codigo == "TUPAD"
    assert carrera.tenant_id == tenant_a.id
    assert carrera.estado == "Activa"


@pytest.mark.asyncio
async def test_crear_carrera_duplicada_lanza_conflict(svc_session):
    """crear_carrera() con código duplicado en el tenant lanza ConflictError."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    await svc.crear_carrera(codigo="DUP", nombre="Primera")

    with pytest.raises(ConflictError):
        await svc.crear_carrera(codigo="DUP", nombre="Duplicada")


@pytest.mark.asyncio
async def test_actualizar_carrera_cambia_estado(svc_session):
    """actualizar_carrera() puede cambiar el estado de Activa a Inactiva."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    carrera = await svc.crear_carrera(codigo="MOD", nombre="Modificable")
    await session.commit()

    actualizada = await svc.actualizar_carrera(carrera.id, estado="Inactiva")
    assert actualizada is not None
    assert actualizada.estado == "Inactiva"


@pytest.mark.asyncio
async def test_obtener_carrera_de_otro_tenant_lanza_not_found(svc_session):
    """obtener_carrera() de otro tenant lanza NotFoundError."""
    session, tenant_a, tenant_b = svc_session

    svc_b = EstructuraService(session=session, tenant_id=tenant_b.id)
    carrera_b = await svc_b.crear_carrera(codigo="CB", nombre="Carrera B")
    await session.commit()

    svc_a = EstructuraService(session=session, tenant_id=tenant_a.id)
    with pytest.raises(NotFoundError):
        await svc_a.obtener_carrera(carrera_b.id)


# ---------------------------------------------------------------------------
# Cohorte — regla de negocio crítica
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_cohorte_activa_en_carrera_inactiva_lanza_business_rule_error(svc_session):
    """crear_cohorte() con carrera Inactiva y estado Activa lanza BusinessRuleError."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    carrera = await svc.crear_carrera(codigo="INA", nombre="Inactiva")
    await svc.actualizar_carrera(carrera.id, estado="Inactiva")
    await session.commit()

    with pytest.raises(BusinessRuleError):
        await svc.crear_cohorte(
            carrera_id=carrera.id,
            nombre="MAR-2026",
            anio=2026,
            vig_desde=date(2026, 3, 1),
        )


@pytest.mark.asyncio
async def test_crear_cohorte_en_carrera_activa_funciona(svc_session):
    """crear_cohorte() en carrera Activa crea la cohorte correctamente."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    carrera = await svc.crear_carrera(codigo="ACT", nombre="Activa")
    await session.commit()

    cohorte = await svc.crear_cohorte(
        carrera_id=carrera.id,
        nombre="AGO-2026",
        anio=2026,
        vig_desde=date(2026, 8, 1),
    )

    assert cohorte.id is not None
    assert cohorte.carrera_id == carrera.id
    assert cohorte.estado == "Activa"


@pytest.mark.asyncio
async def test_inactivar_carrera_no_afecta_cohortes_existentes(svc_session):
    """Inactivar una carrera no cambia el estado de las cohortes ya creadas."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    carrera = await svc.crear_carrera(codigo="HIST", nombre="Historia")
    await session.commit()

    cohorte = await svc.crear_cohorte(
        carrera_id=carrera.id,
        nombre="MAR-2025",
        anio=2025,
        vig_desde=date(2025, 3, 1),
    )
    await session.commit()

    await svc.actualizar_carrera(carrera.id, estado="Inactiva")
    await session.commit()

    cohorte_recargada = await svc.obtener_cohorte(cohorte.id)
    assert cohorte_recargada.estado == "Activa"


# ---------------------------------------------------------------------------
# Materia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_materia_devuelve_entidad_persistida(svc_session):
    """crear_materia() crea y devuelve la materia con los datos correctos."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    materia = await svc.crear_materia(codigo="PROG_I", nombre="Programación I")

    assert materia.id is not None
    assert materia.codigo == "PROG_I"
    assert materia.estado == "Activa"


@pytest.mark.asyncio
async def test_crear_materia_duplicada_lanza_conflict(svc_session):
    """crear_materia() con código duplicado lanza ConflictError."""
    session, tenant_a, _ = svc_session

    svc = EstructuraService(session=session, tenant_id=tenant_a.id)
    await svc.crear_materia(codigo="DUP_M", nombre="Primera")

    with pytest.raises(ConflictError):
        await svc.crear_materia(codigo="DUP_M", nombre="Duplicada")


@pytest.mark.asyncio
async def test_obtener_materia_de_otro_tenant_lanza_not_found(svc_session):
    """obtener_materia() de otro tenant lanza NotFoundError."""
    session, tenant_a, tenant_b = svc_session

    svc_b = EstructuraService(session=session, tenant_id=tenant_b.id)
    materia_b = await svc_b.crear_materia(codigo="MB", nombre="Materia B")
    await session.commit()

    svc_a = EstructuraService(session=session, tenant_id=tenant_a.id)
    with pytest.raises(NotFoundError):
        await svc_a.obtener_materia(materia_b.id)
