"""TDD tests for the audit_action helper function.

Covers:
- audit_action creates a record with action code and filas_afectadas
- audit_action with detalle JSON persists the JSON correctly
- audit_action without materia_id persists NULL
- Multi-tenant isolation: records from tenant A are NOT visible from tenant B
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import get_session_factory, initialize_database
from app.models import AuditLog, AuthUser, Permiso, Rol, RolPermiso, Tenant
from app.models.auth import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential


@pytest.fixture
async def audit_helper_session(valid_env):
    """Set up DB with two tenants for isolation testing."""
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

        tenant_a = Tenant(name="Tenant A", slug="tenant-a")
        tenant_b = Tenant(name="Tenant B", slug="tenant-b")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        from app.core.security import hash_password
        user_a = AuthUser(
            tenant_id=tenant_a.id,
            email="actor@tenant-a.test",
            password_hash=hash_password("Pass1!"),
            roles=["ADMIN"],
            is_active=True,
        )
        user_b = AuthUser(
            tenant_id=tenant_b.id,
            email="actor@tenant-b.test",
            password_hash=hash_password("Pass1!"),
            roles=["ADMIN"],
            is_active=True,
        )
        session.add_all([user_a, user_b])
        await session.flush()

        yield session, tenant_a, tenant_b, user_a, user_b

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
async def test_audit_action_creates_record_with_code_and_filas(audit_helper_session):
    """audit_action creates a record with the given accion code and filas_afectadas."""
    from app.core.audit import audit_action

    session, tenant_a, _, user_a, _ = audit_helper_session

    await audit_action(
        session=session,
        actor_id=user_a.id,
        tenant_id=tenant_a.id,
        accion="CALIFICACIONES_IMPORTAR",
        filas_afectadas=42,
    )

    entry = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_a.id)
        .where(AuditLog.accion == "CALIFICACIONES_IMPORTAR")
    )

    assert entry is not None
    assert entry.accion == "CALIFICACIONES_IMPORTAR"
    assert entry.filas_afectadas == 42
    assert entry.actor_id == user_a.id


@pytest.mark.asyncio
async def test_audit_action_with_detalle_json_persists_correctly(audit_helper_session):
    """audit_action with detalle dict persists JSON correctly."""
    from app.core.audit import audit_action

    session, tenant_a, _, user_a, _ = audit_helper_session
    detalle = {"materia": "PROG_I", "version": "v3"}

    await audit_action(
        session=session,
        actor_id=user_a.id,
        tenant_id=tenant_a.id,
        accion="PADRON_CARGAR",
        detalle=detalle,
    )

    entry = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_a.id)
        .where(AuditLog.accion == "PADRON_CARGAR")
    )

    assert entry is not None
    assert entry.detalle == detalle


@pytest.mark.asyncio
async def test_audit_action_without_materia_id_persists_null(audit_helper_session):
    """audit_action without materia_id stores NULL in materia_id column."""
    from app.core.audit import audit_action

    session, tenant_a, _, user_a, _ = audit_helper_session

    await audit_action(
        session=session,
        actor_id=user_a.id,
        tenant_id=tenant_a.id,
        accion="USUARIO_CREAR",
    )

    entry = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_a.id)
        .where(AuditLog.accion == "USUARIO_CREAR")
    )

    assert entry is not None
    assert entry.materia_id is None


@pytest.mark.asyncio
async def test_audit_records_of_tenant_a_not_visible_from_tenant_b(audit_helper_session):
    """Records created for tenant A do NOT appear when queried from tenant B."""
    from app.core.audit import audit_action
    from app.repositories.audit import AuditLogRepository

    session, tenant_a, tenant_b, user_a, _ = audit_helper_session

    await audit_action(
        session=session,
        actor_id=user_a.id,
        tenant_id=tenant_a.id,
        accion="ACCION_TENANT_A",
    )

    repo_b = AuditLogRepository(session=session, tenant_id=tenant_b.id)
    entries_b = await repo_b.list()

    assert not any(e.accion == "ACCION_TENANT_A" for e in entries_b)


@pytest.mark.asyncio
async def test_audit_action_with_materia_id_persists_correctly(audit_helper_session):
    """audit_action with materia_id stores the UUID correctly."""
    from app.core.audit import audit_action

    session, tenant_a, _, user_a, _ = audit_helper_session
    materia_id = uuid.uuid4()

    await audit_action(
        session=session,
        actor_id=user_a.id,
        tenant_id=tenant_a.id,
        accion="CALIFICACIONES_IMPORTAR",
        materia_id=materia_id,
        filas_afectadas=5,
    )

    entry = await session.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_a.id)
        .where(AuditLog.accion == "CALIFICACIONES_IMPORTAR")
    )

    assert entry is not None
    assert entry.materia_id == materia_id
