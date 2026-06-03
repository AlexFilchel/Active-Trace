import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from app.core.database import get_session_factory, initialize_database
from app.models import (
    AuthLoginChallenge,
    AuthPasswordResetToken,
    AuthRefreshSession,
    AuthTotpCredential,
    AuthUser,
    Tenant,
)
from app.repositories import (
    AuthChallengeRepository,
    AuthPasswordResetRepository,
    AuthTotpRepository,
    AuthUserRepository,
)


@pytest.fixture
async def auth_repository_session(valid_env):
    engine = initialize_database()

    async with engine.begin() as connection:
        await connection.run_sync(Tenant.__table__.create, checkfirst=True)
        await connection.run_sync(AuthUser.__table__.create, checkfirst=True)
        await connection.run_sync(AuthRefreshSession.__table__.create, checkfirst=True)
        await connection.run_sync(AuthTotpCredential.__table__.create, checkfirst=True)
        await connection.run_sync(AuthLoginChallenge.__table__.create, checkfirst=True)
        await connection.run_sync(AuthPasswordResetToken.__table__.create, checkfirst=True)

    session_factory = get_session_factory()

    async with session_factory() as session:
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

        yield session

        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()


@pytest.mark.asyncio
async def test_auth_user_repository_is_tenant_scoped_and_excludes_soft_deleted(auth_repository_session):
    tenant_a = Tenant(name="Tenant A", slug="auth-tenant-a")
    tenant_b = Tenant(name="Tenant B", slug="auth-tenant-b")
    auth_repository_session.add_all([tenant_a, tenant_b])
    await auth_repository_session.flush()

    repo_a = AuthUserRepository(session=auth_repository_session, tenant_id=tenant_a.id)
    repo_b = AuthUserRepository(session=auth_repository_session, tenant_id=tenant_b.id)

    visible = await repo_a.create_user(email="Docente@Example.com", password_hash="hash-a", roles=["PROFESOR"])
    deleted = await repo_a.create_user(email="deleted@example.com", password_hash="hash-b", roles=["ADMIN"])
    await repo_b.create_user(email="docente@example.com", password_hash="hash-c", roles=["PROFESOR"])
    await repo_a.soft_delete(deleted.id)
    await auth_repository_session.commit()

    resolved = await repo_a.get_active_by_email(" docente@example.com ")
    rows = await repo_a.list()

    assert resolved is not None
    assert resolved.id == visible.id
    assert resolved.tenant_id == tenant_a.id
    assert len(rows) == 1
    assert rows[0].email == "docente@example.com"


@pytest.mark.asyncio
async def test_token_and_secret_repositories_do_not_persist_plaintext_values(auth_repository_session):
    tenant = Tenant(name="Tenant C", slug="auth-tenant-c")
    auth_repository_session.add(tenant)
    await auth_repository_session.flush()

    user_repo = AuthUserRepository(session=auth_repository_session, tenant_id=tenant.id)
    user = await user_repo.create_user(email="owner@example.com", password_hash="hash", roles=["ADMIN"])

    challenge_repo = AuthChallengeRepository(session=auth_repository_session, tenant_id=tenant.id)
    reset_repo = AuthPasswordResetRepository(session=auth_repository_session, tenant_id=tenant.id)
    totp_repo = AuthTotpRepository(session=auth_repository_session, tenant_id=tenant.id)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    family_id = uuid.uuid4()

    refresh_session = await user_repo.create_refresh_session(
        user_id=user.id,
        raw_refresh_token="plain-refresh-token",
        expires_at=expires_at,
        family_id=family_id,
    )
    challenge = await challenge_repo.create_challenge(
        user_id=user.id,
        raw_challenge_token="plain-challenge-token",
        expires_at=expires_at,
    )
    reset_token = await reset_repo.create_token(
        user_id=user.id,
        raw_token="plain-reset-token",
        expires_at=expires_at,
    )
    credential = await totp_repo.upsert_secret(user_id=user.id, plaintext_secret="PLAINSECRET123")
    await auth_repository_session.commit()

    stored_refresh_hash = await auth_repository_session.scalar(
        select(AuthRefreshSession.token_hash).where(AuthRefreshSession.id == refresh_session.id)
    )
    stored_challenge_hash = await auth_repository_session.scalar(
        select(AuthLoginChallenge.challenge_hash).where(AuthLoginChallenge.id == challenge.id)
    )
    stored_reset_hash = await auth_repository_session.scalar(
        select(AuthPasswordResetToken.token_hash).where(AuthPasswordResetToken.id == reset_token.id)
    )
    stored_secret = await auth_repository_session.scalar(
        select(AuthTotpCredential.secret_encrypted).where(AuthTotpCredential.id == credential.id)
    )

    assert stored_refresh_hash != "plain-refresh-token"
    assert stored_challenge_hash != "plain-challenge-token"
    assert stored_reset_hash != "plain-reset-token"
    assert stored_secret != "PLAINSECRET123"


@pytest.mark.asyncio
async def test_refresh_sessions_are_soft_deleted_and_tenant_scoped(auth_repository_session):
    tenant_a = Tenant(name="Tenant D", slug="auth-tenant-d")
    tenant_b = Tenant(name="Tenant E", slug="auth-tenant-e")
    auth_repository_session.add_all([tenant_a, tenant_b])
    await auth_repository_session.flush()

    repo_a = AuthUserRepository(session=auth_repository_session, tenant_id=tenant_a.id)
    repo_b = AuthUserRepository(session=auth_repository_session, tenant_id=tenant_b.id)
    user_a = await repo_a.create_user(email="a@example.com", password_hash="hash-a", roles=["ADMIN"])
    user_b = await repo_b.create_user(email="b@example.com", password_hash="hash-b", roles=["ADMIN"])
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    session_a = await repo_a.create_refresh_session(
        user_id=user_a.id,
        raw_refresh_token="tenant-a-token",
        expires_at=expires_at,
        family_id=uuid.uuid4(),
    )
    await repo_b.create_refresh_session(
        user_id=user_b.id,
        raw_refresh_token="tenant-b-token",
        expires_at=expires_at,
        family_id=uuid.uuid4(),
    )
    await repo_a.soft_delete_refresh_session(session_a.id)
    await auth_repository_session.commit()

    active_a = await repo_a.list_active_refresh_sessions(user_id=user_a.id)
    deleted_visible = await repo_a.list_refresh_sessions(user_id=user_a.id, include_deleted=True)

    assert active_a == []
    assert len(deleted_visible) == 1
    assert deleted_visible[0].deleted_at is not None
    assert deleted_visible[0].tenant_id == tenant_a.id
