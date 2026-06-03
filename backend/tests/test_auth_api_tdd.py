from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import get_session_factory, initialize_database
from app.core.security import decode_access_token, generate_totp_code, hash_password
from app.models import (
    AuthLoginChallenge,
    AuthPasswordResetToken,
    AuthRefreshSession,
    AuthTotpCredential,
    AuthUser,
    Tenant,
)


@dataclass
class DeliverySpy:
    sent: list[dict[str, str]] = field(default_factory=list)

    async def send_password_reset(self, *, email: str, token: str) -> None:
        self.sent.append({"email": email, "token": token})


class FrozenClock:
    def __init__(self, start: datetime):
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, *, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)


@pytest.fixture
async def auth_client(valid_env):
    from app.main import create_app
    from app.services.auth import InMemoryLoginRateLimiter

    engine = initialize_database()
    tables = [
        Tenant.__table__,
        AuthUser.__table__,
        AuthRefreshSession.__table__,
        AuthTotpCredential.__table__,
        AuthLoginChallenge.__table__,
        AuthPasswordResetToken.__table__,
    ]

    async with engine.begin() as connection:
        for table in tables:
            await connection.run_sync(table.create, checkfirst=True)

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(AuthPasswordResetToken))
        await session.execute(delete(AuthLoginChallenge))
        await session.execute(delete(AuthTotpCredential))
        await session.execute(delete(AuthRefreshSession))
        await session.execute(delete(AuthUser))
        await session.execute(delete(Tenant))
        await session.commit()

    app = create_app()
    app.state.recovery_delivery = DeliverySpy()
    app.state.login_rate_limiter = InMemoryLoginRateLimiter(
        max_attempts=5,
        window_seconds=60,
        now_provider=FrozenClock(datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)).now,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, app


async def seed_user(*, email: str, password: str, roles: list[str], is_active: bool = True) -> tuple[Tenant, AuthUser]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        tenant = Tenant(name=f"Tenant {email}", slug=f"tenant-{uuid.uuid4()}")
        session.add(tenant)
        await session.flush()

        user = AuthUser(
            tenant_id=tenant.id,
            email=email.lower(),
            password_hash=hash_password(password),
            roles=roles,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        await session.refresh(tenant)
        return tenant, user


@pytest.mark.asyncio
async def test_login_success_invalid_credentials_and_schema_validation(auth_client):
    client, _app = auth_client
    tenant, user = await seed_user(email="Admin@example.com", password="CorrectPass1!", roles=["ADMIN"])

    response = await client.post("/api/auth/login", json={"email": "Admin@example.com", "password": "CorrectPass1!"})

    assert response.status_code == 200
    payload = response.json()
    access_claims = decode_access_token(payload["access_token"])
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 900
    assert payload["requires_two_factor"] is False
    assert set(payload) >= {"access_token", "refresh_token", "token_type", "expires_in", "requires_two_factor"}
    assert access_claims["user_id"] == str(user.id)
    assert access_claims["tenant_id"] == str(tenant.id)
    assert access_claims["roles"] == ["ADMIN"]
    assert "permissions" not in access_claims

    bad_password = await client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    missing_user = await client.post("/api/auth/login", json={"email": "missing@example.com", "password": "wrong"})
    inactive_tenant, inactive_user = await seed_user(email="inactive@example.com", password="CorrectPass1!", roles=["ADMIN"], is_active=False)
    inactive = await client.post("/api/auth/login", json={"email": inactive_user.email, "password": "CorrectPass1!"})
    extra_field = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "CorrectPass1!", "tenant_id": str(inactive_tenant.id)},
    )

    assert bad_password.status_code == 401
    assert missing_user.status_code == 401
    assert inactive.status_code == 401
    assert bad_password.json() == missing_user.json() == inactive.json()
    assert extra_field.status_code == 422


@pytest.mark.asyncio
async def test_login_requires_tenant_disambiguation_when_email_exists_in_multiple_tenants(auth_client):
    client, _app = auth_client
    tenant_a, user_a = await seed_user(email="shared@example.com", password="TenantOnePass1!", roles=["ADMIN"])
    tenant_b, user_b = await seed_user(email="shared@example.com", password="TenantTwoPass2!", roles=["PROFESOR"])

    ambiguous = await client.post(
        "/api/auth/login",
        json={"email": "shared@example.com", "password": "TenantOnePass1!"},
    )
    tenant_a_login = await client.post(
        "/api/auth/login",
        json={"email": "shared@example.com", "password": "TenantOnePass1!", "tenant_slug": tenant_a.slug},
    )
    tenant_b_login = await client.post(
        "/api/auth/login",
        json={"email": "shared@example.com", "password": "TenantTwoPass2!", "tenant_slug": tenant_b.slug},
    )

    assert ambiguous.status_code == 401
    assert tenant_a_login.status_code == 200
    assert tenant_b_login.status_code == 200

    tenant_a_claims = decode_access_token(tenant_a_login.json()["access_token"])
    tenant_b_claims = decode_access_token(tenant_b_login.json()["access_token"])

    assert tenant_a_claims["tenant_id"] == str(tenant_a.id)
    assert tenant_a_claims["user_id"] == str(user_a.id)
    assert tenant_b_claims["tenant_id"] == str(tenant_b.id)
    assert tenant_b_claims["user_id"] == str(user_b.id)


@pytest.mark.asyncio
async def test_refresh_rotation_reuse_detection_and_logout(auth_client):
    client, _app = auth_client
    await seed_user(email="rotate@example.com", password="CorrectPass1!", roles=["COORDINADOR"])

    login = await client.post("/api/auth/login", json={"email": "rotate@example.com", "password": "CorrectPass1!"})
    first_tokens = login.json()
    refresh = await client.post("/api/auth/refresh", json={"refresh_token": first_tokens["refresh_token"]})

    assert refresh.status_code == 200
    rotated_tokens = refresh.json()
    assert rotated_tokens["refresh_token"] != first_tokens["refresh_token"]

    reused = await client.post("/api/auth/refresh", json={"refresh_token": first_tokens["refresh_token"]})
    descendant = await client.post("/api/auth/refresh", json={"refresh_token": rotated_tokens["refresh_token"]})

    assert reused.status_code == 401
    assert descendant.status_code == 401

    second_login = await client.post("/api/auth/login", json={"email": "rotate@example.com", "password": "CorrectPass1!"})
    second_tokens = second_login.json()
    logout = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {second_tokens['access_token']}"},
        json={"refresh_token": second_tokens["refresh_token"]},
    )
    after_logout = await client.post("/api/auth/refresh", json={"refresh_token": second_tokens["refresh_token"]})

    assert logout.status_code == 204
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_totp_enrollment_and_login_gate(auth_client):
    client, _app = auth_client
    _tenant, user = await seed_user(email="mfa@example.com", password="CorrectPass1!", roles=["ADMIN"])

    pre_login = await client.post("/api/auth/login", json={"email": "mfa@example.com", "password": "CorrectPass1!"})
    access_token = pre_login.json()["access_token"]

    enroll = await client.post("/api/auth/2fa/enroll", headers={"Authorization": f"Bearer {access_token}"})

    assert enroll.status_code == 200
    secret = enroll.json()["secret"]
    assert enroll.json()["provisioning_uri"].startswith("otpauth://totp/")

    enable = await client.post(
        "/api/auth/2fa/verify-enrollment",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"code": generate_totp_code(secret)},
    )

    assert enable.status_code == 200
    assert enable.json() == {"enabled": True}

    gated_login = await client.post("/api/auth/login", json={"email": user.email, "password": "CorrectPass1!"})

    assert gated_login.status_code == 200
    assert gated_login.json()["requires_two_factor"] is True
    assert "access_token" not in gated_login.json()

    invalid_verify = await client.post(
        "/api/auth/2fa/verify-login",
        json={"challenge_token": gated_login.json()["challenge_token"], "code": "000000"},
    )
    valid_verify = await client.post(
        "/api/auth/2fa/verify-login",
        json={"challenge_token": gated_login.json()["challenge_token"], "code": generate_totp_code(secret)},
    )

    assert invalid_verify.status_code == 401
    assert valid_verify.status_code == 200
    assert set(valid_verify.json()) >= {"access_token", "refresh_token"}


@pytest.mark.asyncio
async def test_password_reset_rejects_expired_tokens_at_runtime(auth_client):
    client, app = auth_client
    clock = FrozenClock(datetime(2026, 6, 2, 16, 0, tzinfo=timezone.utc))
    app.state.now_provider = clock.now
    await seed_user(email="expired-reset@example.com", password="CorrectPass1!", roles=["ADMIN"])

    forgot = await client.post("/api/auth/forgot", json={"email": "expired-reset@example.com"})
    expired_token = app.state.recovery_delivery.sent[0]["token"]

    clock.advance(seconds=901)
    expired_reset = await client.post(
        "/api/auth/reset",
        json={"token": expired_token, "new_password": "ExpiredPass2!"},
    )
    old_password_login = await client.post(
        "/api/auth/login",
        json={"email": "expired-reset@example.com", "password": "CorrectPass1!"},
    )

    fresh_forgot = await client.post("/api/auth/forgot", json={"email": "expired-reset@example.com"})
    fresh_token = app.state.recovery_delivery.sent[1]["token"]
    fresh_reset = await client.post(
        "/api/auth/reset",
        json={"token": fresh_token, "new_password": "FreshPass3!"},
    )
    new_password_login = await client.post(
        "/api/auth/login",
        json={"email": "expired-reset@example.com", "password": "FreshPass3!"},
    )

    assert forgot.status_code == 202
    assert expired_reset.status_code == 401
    assert old_password_login.status_code == 200
    assert fresh_forgot.status_code == 202
    assert fresh_reset.status_code == 200
    assert new_password_login.status_code == 200


@pytest.mark.asyncio
async def test_password_recovery_uses_one_time_tokens_updates_password_and_revokes_sessions(auth_client):
    client, app = auth_client
    await seed_user(email="recover@example.com", password="CorrectPass1!", roles=["ADMIN"])

    login = await client.post("/api/auth/login", json={"email": "recover@example.com", "password": "CorrectPass1!"})
    original_refresh = login.json()["refresh_token"]

    forgot_existing = await client.post("/api/auth/forgot", json={"email": "recover@example.com"})
    forgot_missing = await client.post("/api/auth/forgot", json={"email": "missing@example.com"})

    assert forgot_existing.status_code == 202
    assert forgot_missing.status_code == 202
    assert forgot_existing.json() == forgot_missing.json()
    assert len(app.state.recovery_delivery.sent) == 1

    delivered_token = app.state.recovery_delivery.sent[0]["token"]
    session_factory = get_session_factory()
    async with session_factory() as session:
        stored_hash = await session.scalar(select(AuthPasswordResetToken.token_hash))
    assert stored_hash != delivered_token

    reset = await client.post("/api/auth/reset", json={"token": delivered_token, "new_password": "EvenBetterPass2!"})
    reused = await client.post("/api/auth/reset", json={"token": delivered_token, "new_password": "ThirdPass3!"})
    old_login = await client.post("/api/auth/login", json={"email": "recover@example.com", "password": "CorrectPass1!"})
    new_login = await client.post("/api/auth/login", json={"email": "recover@example.com", "password": "EvenBetterPass2!"})
    old_refresh_after_reset = await client.post("/api/auth/refresh", json={"refresh_token": original_refresh})

    assert reset.status_code == 200
    assert reused.status_code == 401
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    assert old_refresh_after_reset.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit_is_bucketed_by_ip_and_email_without_enumeration(auth_client):
    client, app = auth_client
    clock = FrozenClock(datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc))
    from app.services.auth import InMemoryLoginRateLimiter

    app.state.login_rate_limiter = InMemoryLoginRateLimiter(max_attempts=5, window_seconds=60, now_provider=clock.now)
    await seed_user(email="limited@example.com", password="CorrectPass1!", roles=["ADMIN"])

    statuses = []
    for _ in range(6):
        response = await client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": "10.1.1.1"},
            json={"email": "limited@example.com", "password": "wrong"},
        )
        statuses.append(response.status_code)

    different_email = await client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "10.1.1.1"},
        json={"email": "other@example.com", "password": "wrong"},
    )
    unknown_statuses = []
    for _ in range(6):
        response = await client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": "10.9.9.9"},
            json={"email": "unknown@example.com", "password": "wrong"},
        )
        unknown_statuses.append(response.status_code)

    clock.advance(seconds=61)
    after_window = await client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "10.1.1.1"},
        json={"email": "limited@example.com", "password": "wrong"},
    )

    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
    assert different_email.status_code == 401
    assert unknown_statuses[:5] == [401, 401, 401, 401, 401]
    assert unknown_statuses[5] == 429
    assert after_window.status_code == 401
