from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_value, encrypt_value, hash_token
from app.models import AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Tenant
from app.models.base import utc_now
from app.repositories.tenant_scoped import TenantScopedRepository


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_slug(slug: str) -> str:
    return slug.strip().lower()


class AuthIdentityRepository:
    def __init__(self, *, session: AsyncSession):
        self.session = session

    async def find_unique_active_by_email(self, email: str, tenant_slug: str | None = None) -> AuthUser | None:
        statement = (
            select(AuthUser)
            .join(Tenant, Tenant.id == AuthUser.tenant_id)
            .where(
                AuthUser.email == normalize_email(email),
                AuthUser.is_active.is_(True),
                AuthUser.deleted_at.is_(None),
            )
            .order_by(AuthUser.created_at.asc())
        )
        if tenant_slug is not None:
            statement = statement.where(Tenant.slug == normalize_slug(tenant_slug), Tenant.deleted_at.is_(None))
            return await self.session.scalar(statement)
        rows = list((await self.session.scalars(statement)).all())
        return rows[0] if len(rows) == 1 else None

    async def get_user_by_id(self, *, user_id: uuid.UUID, tenant_id: uuid.UUID) -> AuthUser | None:
        statement = select(AuthUser).where(
            AuthUser.id == user_id,
            AuthUser.tenant_id == tenant_id,
            AuthUser.is_active.is_(True),
            AuthUser.deleted_at.is_(None),
        )
        return await self.session.scalar(statement)


class AuthUserRepository(TenantScopedRepository[AuthUser]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=AuthUser, tenant_id=tenant_id)

    async def create_user(self, *, email: str, password_hash: str, roles: list[str], is_active: bool = True) -> AuthUser:
        return await self.create(
            email=normalize_email(email),
            password_hash=password_hash,
            roles=roles,
            is_active=is_active,
        )

    async def get_active_by_email(self, email: str) -> AuthUser | None:
        statement = self._base_query().where(AuthUser.email == normalize_email(email), AuthUser.is_active.is_(True))
        return await self.session.scalar(statement)

    async def get_active_by_id(self, user_id: uuid.UUID) -> AuthUser | None:
        statement = self._base_query().where(AuthUser.id == user_id, AuthUser.is_active.is_(True))
        return await self.session.scalar(statement)

    async def update_password_hash(self, *, user_id: uuid.UUID, password_hash: str) -> AuthUser | None:
        entity = await self.get_active_by_id(user_id)
        if entity is None:
            return None
        entity.password_hash = password_hash
        await self.session.flush()
        return entity

    async def create_refresh_session(
        self,
        *,
        user_id: uuid.UUID,
        raw_refresh_token: str,
        expires_at: datetime,
        family_id: uuid.UUID,
        replaced_by_session_id: uuid.UUID | None = None,
    ) -> AuthRefreshSession:
        entity = AuthRefreshSession(
            tenant_id=self.context.tenant_id,
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=expires_at,
            replaced_by_session_id=replaced_by_session_id,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_active_refresh_sessions(self, *, user_id: uuid.UUID) -> list[AuthRefreshSession]:
        statement = (
            select(AuthRefreshSession)
            .where(
                AuthRefreshSession.tenant_id == self.context.tenant_id,
                AuthRefreshSession.user_id == user_id,
                AuthRefreshSession.deleted_at.is_(None),
            )
            .order_by(AuthRefreshSession.created_at.asc())
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def list_refresh_sessions(self, *, user_id: uuid.UUID, include_deleted: bool = False) -> list[AuthRefreshSession]:
        statement = select(AuthRefreshSession).where(
            AuthRefreshSession.tenant_id == self.context.tenant_id,
            AuthRefreshSession.user_id == user_id,
        )
        if not include_deleted:
            statement = statement.where(AuthRefreshSession.deleted_at.is_(None))
        result = await self.session.scalars(statement.order_by(AuthRefreshSession.created_at.asc()))
        return list(result.all())

    async def soft_delete_refresh_session(self, session_id: uuid.UUID) -> bool:
        statement = select(AuthRefreshSession).where(
            AuthRefreshSession.id == session_id,
            AuthRefreshSession.tenant_id == self.context.tenant_id,
        )
        entity = await self.session.scalar(statement)
        if entity is None:
            return False
        entity.deleted_at = utc_now()
        await self.session.flush()
        return True


class RefreshSessionRepository:
    def __init__(self, *, session: AsyncSession):
        self.session = session

    async def get_by_raw_token(self, raw_refresh_token: str) -> AuthRefreshSession | None:
        statement = select(AuthRefreshSession).where(AuthRefreshSession.token_hash == hash_token(raw_refresh_token))
        return await self.session.scalar(statement)

    async def mark_rotated(self, *, refresh_session: AuthRefreshSession, replaced_by_session_id: uuid.UUID) -> None:
        refresh_session.used_at = utc_now()
        refresh_session.revoked_at = refresh_session.used_at
        refresh_session.replaced_by_session_id = replaced_by_session_id
        await self.session.flush()

    async def revoke(self, refresh_session: AuthRefreshSession) -> None:
        timestamp = utc_now()
        refresh_session.revoked_at = timestamp
        if refresh_session.deleted_at is None:
            refresh_session.deleted_at = timestamp
        await self.session.flush()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        statement = select(AuthRefreshSession).where(AuthRefreshSession.family_id == family_id)
        for row in list((await self.session.scalars(statement)).all()):
            row.revoked_at = row.revoked_at or utc_now()
            row.deleted_at = row.deleted_at or row.revoked_at
        await self.session.flush()

    async def revoke_user_sessions(self, *, user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        statement = select(AuthRefreshSession).where(
            AuthRefreshSession.user_id == user_id,
            AuthRefreshSession.tenant_id == tenant_id,
            AuthRefreshSession.deleted_at.is_(None),
        )
        timestamp = utc_now()
        for row in list((await self.session.scalars(statement)).all()):
            row.revoked_at = row.revoked_at or timestamp
            row.deleted_at = row.deleted_at or timestamp
        await self.session.flush()


class AuthChallengeRepository(TenantScopedRepository[AuthLoginChallenge]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=AuthLoginChallenge, tenant_id=tenant_id)

    async def create_challenge(self, *, user_id: uuid.UUID, raw_challenge_token: str, expires_at: datetime) -> AuthLoginChallenge:
        return await self.create(user_id=user_id, challenge_hash=hash_token(raw_challenge_token), expires_at=expires_at)


class LoginChallengeRepository:
    def __init__(self, *, session: AsyncSession):
        self.session = session

    async def get_by_raw_token(self, raw_challenge_token: str) -> AuthLoginChallenge | None:
        statement = select(AuthLoginChallenge).where(AuthLoginChallenge.challenge_hash == hash_token(raw_challenge_token))
        return await self.session.scalar(statement)

    async def consume(self, challenge: AuthLoginChallenge) -> None:
        challenge.consumed_at = utc_now()
        challenge.deleted_at = challenge.deleted_at or challenge.consumed_at
        await self.session.flush()


class AuthPasswordResetRepository(TenantScopedRepository[AuthPasswordResetToken]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=AuthPasswordResetToken, tenant_id=tenant_id)

    async def create_token(self, *, user_id: uuid.UUID, raw_token: str, expires_at: datetime) -> AuthPasswordResetToken:
        return await self.create(user_id=user_id, token_hash=hash_token(raw_token), expires_at=expires_at)


class PasswordResetRepository:
    def __init__(self, *, session: AsyncSession):
        self.session = session

    async def get_by_raw_token(self, raw_token: str) -> AuthPasswordResetToken | None:
        statement = select(AuthPasswordResetToken).where(AuthPasswordResetToken.token_hash == hash_token(raw_token))
        return await self.session.scalar(statement)

    async def consume(self, token: AuthPasswordResetToken) -> None:
        token.consumed_at = utc_now()
        token.deleted_at = token.deleted_at or token.consumed_at
        await self.session.flush()


class AuthTotpRepository(TenantScopedRepository[AuthTotpCredential]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID | str | None):
        super().__init__(session=session, model=AuthTotpCredential, tenant_id=tenant_id)

    async def upsert_secret(self, *, user_id: uuid.UUID, plaintext_secret: str) -> AuthTotpCredential:
        statement = self._base_query(include_deleted=True).where(AuthTotpCredential.user_id == user_id)
        entity = await self.session.scalar(statement)

        if entity is None:
            entity = AuthTotpCredential(
                tenant_id=self.context.tenant_id,
                user_id=user_id,
                secret_encrypted=encrypt_value(plaintext_secret),
            )
            self.session.add(entity)
        else:
            entity.secret_encrypted = encrypt_value(plaintext_secret)
            entity.is_enabled = False
            entity.confirmed_at = None
            entity.deleted_at = None

        await self.session.flush()
        return entity

    async def get_by_user_id(self, user_id: uuid.UUID) -> AuthTotpCredential | None:
        statement = self._base_query(include_deleted=True).where(AuthTotpCredential.user_id == user_id)
        return await self.session.scalar(statement)

    async def enable(self, credential: AuthTotpCredential) -> AuthTotpCredential:
        credential.is_enabled = True
        credential.confirmed_at = utc_now()
        await self.session.flush()
        return credential

    async def decrypt_secret(self, credential: AuthTotpCredential) -> str:
        return decrypt_value(credential.secret_encrypted)
