"""TDD tests for AuditLog model and AuditLogRepository.

Covers:
- AuditLog can be created with all its fields
- AuditLog does NOT have deleted_at or updated_at
- AuditLogRepository does NOT expose update/soft_delete/delete methods
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import get_session_factory, initialize_database
from app.models import AuditLog, AuthUser, Permiso, Rol, RolPermiso, Tenant
from app.models.auth import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential
from app.repositories.audit import AuditLogRepository


@pytest.fixture
async def audit_db_session(valid_env):
    """Set up DB with all tables and a tenant + user for testing."""
    from app.models.audit import AuditLog as AuditLogModel

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
        await conn.run_sync(AuditLogModel.__table__.create, checkfirst=True)

    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import text
        await session.execute(text("TRUNCATE TABLE audit_log"))
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

        tenant = Tenant(name="Audit Test Tenant", slug="audit-test")
        session.add(tenant)
        await session.flush()

        from app.core.security import hash_password
        user = AuthUser(
            tenant_id=tenant.id,
            email="actor@audit.test",
            password_hash=hash_password("Pass1!"),
            roles=["ADMIN"],
            is_active=True,
        )
        session.add(user)
        await session.flush()

        yield session, tenant, user

        from sqlalchemy import text
        await session.execute(text("TRUNCATE TABLE audit_log"))
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()


@pytest.mark.asyncio
async def test_audit_log_can_be_created_with_all_fields(audit_db_session):
    """AuditLog can be created and persisted with all expected fields."""
    session, tenant, user = audit_db_session

    log = AuditLog(
        tenant_id=tenant.id,
        actor_id=user.id,
        accion="CALIFICACIONES_IMPORTAR",
        detalle={"materia": "PROG_I"},
        filas_afectadas=42,
        ip="192.168.1.1",
        user_agent="pytest/1.0",
    )
    session.add(log)
    await session.flush()

    persisted = await session.scalar(select(AuditLog).where(AuditLog.id == log.id))

    assert persisted is not None
    assert persisted.tenant_id == tenant.id
    assert persisted.actor_id == user.id
    assert persisted.accion == "CALIFICACIONES_IMPORTAR"
    assert persisted.detalle == {"materia": "PROG_I"}
    assert persisted.filas_afectadas == 42
    assert persisted.ip == "192.168.1.1"
    assert persisted.user_agent == "pytest/1.0"
    assert persisted.fecha_hora is not None


@pytest.mark.asyncio
async def test_audit_log_does_not_have_deleted_at_or_updated_at(audit_db_session):
    """AuditLog model MUST NOT have deleted_at or updated_at columns."""
    column_names = set(AuditLog.__table__.columns.keys())

    assert "deleted_at" not in column_names, "AuditLog must not have deleted_at"
    assert "updated_at" not in column_names, "AuditLog must not have updated_at"


@pytest.mark.asyncio
async def test_audit_log_has_expected_columns(audit_db_session):
    """AuditLog model has all required columns from E-AUD spec."""
    column_names = set(AuditLog.__table__.columns.keys())

    assert column_names >= {
        "id",
        "tenant_id",
        "fecha_hora",
        "actor_id",
        "impersonado_id",
        "materia_id",
        "accion",
        "detalle",
        "filas_afectadas",
        "ip",
        "user_agent",
    }


@pytest.mark.asyncio
async def test_audit_log_repository_does_not_expose_mutation_methods(audit_db_session):
    """AuditLogRepository must NOT expose update, soft_delete, or delete methods."""
    session, tenant, _ = audit_db_session
    repo = AuditLogRepository(session=session, tenant_id=tenant.id)

    assert not hasattr(repo, "update"), "AuditLogRepository must not have update()"
    assert not hasattr(repo, "soft_delete"), "AuditLogRepository must not have soft_delete()"
    assert not hasattr(repo, "delete"), "AuditLogRepository must not have delete()"


@pytest.mark.asyncio
async def test_audit_log_repository_create_and_list(audit_db_session):
    """AuditLogRepository.create() persists and list() retrieves by tenant."""
    session, tenant, user = audit_db_session
    repo = AuditLogRepository(session=session, tenant_id=tenant.id)

    entry = await repo.create(
        actor_id=user.id,
        accion="PADRON_CARGAR",
        filas_afectadas=10,
    )
    await session.flush()

    entries = await repo.list()

    assert entry.id is not None
    assert any(e.id == entry.id for e in entries)
    assert entry.tenant_id == tenant.id


@pytest.mark.asyncio
async def test_audit_log_repository_get_returns_correct_entry(audit_db_session):
    """AuditLogRepository.get() retrieves a specific entry by ID, scoped to tenant."""
    session, tenant, user = audit_db_session
    repo = AuditLogRepository(session=session, tenant_id=tenant.id)

    entry = await repo.create(actor_id=user.id, accion="TEST_GET")
    await session.flush()

    found = await repo.get(entry.id)
    missing = await repo.get(uuid.uuid4())

    assert found is not None
    assert found.id == entry.id
    assert missing is None


@pytest.mark.asyncio
async def test_audit_log_optional_fields_default_to_none(audit_db_session):
    """AuditLog persists with NULL for optional fields when not provided."""
    session, tenant, user = audit_db_session

    log = AuditLog(
        tenant_id=tenant.id,
        actor_id=user.id,
        accion="SIMPLE_ACTION",
    )
    session.add(log)
    await session.flush()

    persisted = await session.scalar(select(AuditLog).where(AuditLog.id == log.id))

    assert persisted.impersonado_id is None
    assert persisted.materia_id is None
    assert persisted.detalle is None
    assert persisted.ip is None
    assert persisted.user_agent is None
    assert persisted.filas_afectadas == 0
