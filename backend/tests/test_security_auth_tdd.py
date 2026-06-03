from datetime import datetime, timedelta, timezone

import pytest

from app.core import security


def test_password_hash_round_trip_and_rejects_wrong_password(valid_env):
    password_hash = security.hash_password("CorrectHorseBatteryStaple1!")

    assert password_hash != "CorrectHorseBatteryStaple1!"
    assert security.verify_password("CorrectHorseBatteryStaple1!", password_hash) is True
    assert security.verify_password("wrong-password", password_hash) is False


def test_access_jwt_signs_minimal_claims_and_rejects_invalid_tokens(valid_env):
    token = security.create_access_token(
        user_id="2fbef596-18bb-4751-a4c2-73a0d7707fea",
        tenant_id="cc986795-9217-435c-9954-92809db2e4ce",
        roles=["ADMIN", "COORDINADOR"],
    )

    claims = security.decode_access_token(token)

    assert claims["user_id"] == "2fbef596-18bb-4751-a4c2-73a0d7707fea"
    assert claims["tenant_id"] == "cc986795-9217-435c-9954-92809db2e4ce"
    assert claims["roles"] == ["ADMIN", "COORDINADOR"]
    assert "permissions" not in claims
    assert datetime.fromtimestamp(claims["exp"], tz=timezone.utc) <= datetime.now(timezone.utc) + timedelta(minutes=15, seconds=5)

    with pytest.raises(security.TokenValidationError):
        security.decode_access_token(token + "tampered")


def test_token_hash_is_deterministic_without_leaking_plaintext(valid_env):
    first = security.hash_token("refresh-secret")
    second = security.hash_token("refresh-secret")
    third = security.hash_token("different-secret")

    assert first == second
    assert first != third
    assert first != "refresh-secret"


def test_totp_generation_and_verification_supports_current_and_invalid_codes(valid_env):
    secret = security.generate_totp_secret()
    code = security.generate_totp_code(secret, now=datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc))

    assert security.verify_totp_code(secret, code, now=datetime(2026, 6, 2, 12, 0, 20, tzinfo=timezone.utc)) is True
    assert security.verify_totp_code(secret, "000000", now=datetime(2026, 6, 2, 12, 0, 20, tzinfo=timezone.utc)) is False


def test_totp_provisioning_uri_contains_issuer_and_account_name(valid_env):
    secret = security.generate_totp_secret()
    uri = security.build_totp_provisioning_uri(secret=secret, account_name="admin@example.com")

    assert uri.startswith("otpauth://totp/")
    assert "issuer=activia-trace" in uri
    assert "admin%40example.com" in uri
