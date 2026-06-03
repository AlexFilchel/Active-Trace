from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    build_totp_provisioning_uri,
    create_access_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)
from app.repositories import (
    AuthChallengeRepository,
    AuthIdentityRepository,
    AuthPasswordResetRepository,
    AuthTotpRepository,
    AuthUserRepository,
    LoginChallengeRepository,
    PasswordResetRepository,
    RefreshSessionRepository,
    normalize_email,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthServiceError(ValueError):
    status_code = 400
    detail = "Authentication request failed."


class InvalidCredentialsError(AuthServiceError):
    status_code = 401
    detail = "Invalid email or password."


class InvalidTokenError(AuthServiceError):
    status_code = 401
    detail = "Token is invalid or expired."


class RateLimitExceededError(AuthServiceError):
    status_code = 429
    detail = "Too many login attempts. Try again later."


@dataclass
class SessionTokens:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    requires_two_factor: bool = False


class NullRecoveryDelivery:
    async def send_password_reset(self, *, email: str, token: str) -> None:
        return None


class InMemoryLoginRateLimiter:
    def __init__(
        self,
        *,
        max_attempts: int = 5,
        window_seconds: int = 60,
        now_provider: Callable[[], datetime] = utc_now,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.now_provider = now_provider
        self._attempts: dict[tuple[str, str], list[datetime]] = defaultdict(list)

    def allow_attempt(self, *, email: str, ip_address: str) -> bool:
        now = self.now_provider()
        window_start = now - timedelta(seconds=self.window_seconds)
        bucket_key = (normalize_email(email), ip_address)
        bucket = [attempt for attempt in self._attempts[bucket_key] if attempt > window_start]
        self._attempts[bucket_key] = bucket
        if len(bucket) >= self.max_attempts:
            return False
        bucket.append(now)
        return True


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        rate_limiter: InMemoryLoginRateLimiter | None = None,
        recovery_delivery: NullRecoveryDelivery | None = None,
        now_provider: Callable[[], datetime] = utc_now,
    ):
        self.session = session
        self.rate_limiter = rate_limiter or InMemoryLoginRateLimiter(now_provider=now_provider)
        self.recovery_delivery = recovery_delivery or NullRecoveryDelivery()
        self.now_provider = now_provider
        self.identity_repository = AuthIdentityRepository(session=session)
        self.refresh_repository = RefreshSessionRepository(session=session)
        self.challenge_lookup_repository = LoginChallengeRepository(session=session)
        self.reset_lookup_repository = PasswordResetRepository(session=session)

    async def login(self, *, email: str, password: str, ip_address: str, tenant_slug: str | None = None) -> dict[str, object]:
        if not self.rate_limiter.allow_attempt(email=email, ip_address=ip_address):
            raise RateLimitExceededError()

        user = await self.identity_repository.find_unique_active_by_email(email, tenant_slug=tenant_slug)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        totp_repository = AuthTotpRepository(session=self.session, tenant_id=user.tenant_id)
        credential = await totp_repository.get_by_user_id(user.id)
        if credential is not None and credential.is_enabled:
            raw_challenge_token = secrets.token_urlsafe(32)
            challenge_repository = AuthChallengeRepository(session=self.session, tenant_id=user.tenant_id)
            await challenge_repository.create_challenge(
                user_id=user.id,
                raw_challenge_token=raw_challenge_token,
                expires_at=self.now_provider() + timedelta(minutes=5),
            )
            await self.session.commit()
            return {
                "requires_two_factor": True,
                "challenge_token": raw_challenge_token,
                "expires_in": 300,
            }

        tokens = await self._issue_tokens(user=user)
        return tokens.__dict__

    async def refresh(self, *, refresh_token: str) -> dict[str, object]:
        existing_session = await self.refresh_repository.get_by_raw_token(refresh_token)
        if existing_session is None:
            raise InvalidTokenError()

        if self._is_refresh_session_compromised(existing_session):
            await self.refresh_repository.revoke_family(existing_session.family_id)
            await self.session.commit()
            raise InvalidTokenError()

        user = await self.identity_repository.get_user_by_id(user_id=existing_session.user_id, tenant_id=existing_session.tenant_id)
        if user is None:
            await self.refresh_repository.revoke_family(existing_session.family_id)
            await self.session.commit()
            raise InvalidTokenError()

        raw_refresh_token = secrets.token_urlsafe(32)
        user_repository = AuthUserRepository(session=self.session, tenant_id=user.tenant_id)
        replacement_session = await user_repository.create_refresh_session(
            user_id=user.id,
            raw_refresh_token=raw_refresh_token,
            expires_at=self.now_provider() + timedelta(days=7),
            family_id=existing_session.family_id,
        )
        await self.refresh_repository.mark_rotated(
            refresh_session=existing_session,
            replaced_by_session_id=replacement_session.id,
        )
        await self.session.commit()

        return SessionTokens(
            access_token=create_access_token(user_id=str(user.id), tenant_id=str(user.tenant_id), roles=user.roles),
            refresh_token=raw_refresh_token,
        ).__dict__

    async def logout(self, *, current_user_id: uuid.UUID, current_tenant_id: uuid.UUID, refresh_token: str) -> None:
        existing_session = await self.refresh_repository.get_by_raw_token(refresh_token)
        if existing_session is None:
            raise InvalidTokenError()
        if existing_session.user_id != current_user_id or existing_session.tenant_id != current_tenant_id:
            raise InvalidTokenError()

        await self.refresh_repository.revoke(existing_session)
        await self.session.commit()

    async def begin_totp_enrollment(self, *, current_user_id: uuid.UUID, current_tenant_id: uuid.UUID, email: str) -> dict[str, str]:
        user_repository = AuthUserRepository(session=self.session, tenant_id=current_tenant_id)
        user = await user_repository.get_active_by_id(current_user_id)
        if user is None:
            raise InvalidTokenError()

        secret = generate_totp_secret()
        totp_repository = AuthTotpRepository(session=self.session, tenant_id=current_tenant_id)
        await totp_repository.upsert_secret(user_id=current_user_id, plaintext_secret=secret)
        await self.session.commit()
        return {
            "secret": secret,
            "provisioning_uri": build_totp_provisioning_uri(secret=secret, account_name=email),
        }

    async def verify_totp_enrollment(self, *, current_user_id: uuid.UUID, current_tenant_id: uuid.UUID, code: str) -> dict[str, bool]:
        totp_repository = AuthTotpRepository(session=self.session, tenant_id=current_tenant_id)
        credential = await totp_repository.get_by_user_id(current_user_id)
        if credential is None:
            raise InvalidTokenError()

        secret = await totp_repository.decrypt_secret(credential)
        if not verify_totp_code(secret, code):
            raise InvalidTokenError()

        await totp_repository.enable(credential)
        await self.session.commit()
        return {"enabled": True}

    async def verify_login_2fa(self, *, challenge_token: str, code: str) -> dict[str, object]:
        challenge = await self.challenge_lookup_repository.get_by_raw_token(challenge_token)
        if challenge is None or challenge.deleted_at is not None or challenge.consumed_at is not None or challenge.expires_at <= self.now_provider():
            raise InvalidTokenError()

        user = await self.identity_repository.get_user_by_id(user_id=challenge.user_id, tenant_id=challenge.tenant_id)
        if user is None:
            raise InvalidTokenError()

        totp_repository = AuthTotpRepository(session=self.session, tenant_id=user.tenant_id)
        credential = await totp_repository.get_by_user_id(user.id)
        if credential is None or not credential.is_enabled:
            raise InvalidTokenError()

        secret = await totp_repository.decrypt_secret(credential)
        if not verify_totp_code(secret, code):
            raise InvalidTokenError()

        await self.challenge_lookup_repository.consume(challenge)
        tokens = await self._issue_tokens(user=user)
        return tokens.__dict__

    async def forgot_password(self, *, email: str) -> dict[str, str]:
        user = await self.identity_repository.find_unique_active_by_email(email)
        if user is not None:
            raw_token = secrets.token_urlsafe(32)
            repository = AuthPasswordResetRepository(session=self.session, tenant_id=user.tenant_id)
            await repository.create_token(
                user_id=user.id,
                raw_token=raw_token,
                expires_at=self.now_provider() + timedelta(minutes=15),
            )
            await self.session.commit()
            await self.recovery_delivery.send_password_reset(email=user.email, token=raw_token)
        return {"message": "If the account exists, recovery instructions were sent."}

    async def reset_password(self, *, token: str, new_password: str) -> dict[str, str]:
        reset_token = await self.reset_lookup_repository.get_by_raw_token(token)
        if (
            reset_token is None
            or reset_token.deleted_at is not None
            or reset_token.consumed_at is not None
            or reset_token.expires_at <= self.now_provider()
        ):
            raise InvalidTokenError()

        user_repository = AuthUserRepository(session=self.session, tenant_id=reset_token.tenant_id)
        user = await user_repository.update_password_hash(user_id=reset_token.user_id, password_hash=hash_password(new_password))
        if user is None:
            raise InvalidTokenError()

        await self.reset_lookup_repository.consume(reset_token)
        await self.refresh_repository.revoke_user_sessions(user_id=user.id, tenant_id=user.tenant_id)
        await self.session.commit()
        return {"message": "Password reset completed."}

    async def _issue_tokens(self, *, user) -> SessionTokens:
        raw_refresh_token = secrets.token_urlsafe(32)
        repository = AuthUserRepository(session=self.session, tenant_id=user.tenant_id)
        await repository.create_refresh_session(
            user_id=user.id,
            raw_refresh_token=raw_refresh_token,
            expires_at=self.now_provider() + timedelta(days=7),
            family_id=uuid.uuid4(),
        )
        await self.session.commit()
        return SessionTokens(
            access_token=create_access_token(user_id=str(user.id), tenant_id=str(user.tenant_id), roles=user.roles),
            refresh_token=raw_refresh_token,
        )

    def _is_refresh_session_compromised(self, refresh_session) -> bool:
        now = self.now_provider()
        return bool(
            refresh_session.deleted_at is not None
            or refresh_session.used_at is not None
            or refresh_session.revoked_at is not None
            or refresh_session.expires_at <= now
        )
