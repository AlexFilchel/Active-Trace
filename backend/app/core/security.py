from __future__ import annotations

import base64
from base64 import urlsafe_b64decode, urlsafe_b64encode
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from urllib.parse import quote

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.core.config import get_settings


class EncryptionError(ValueError):
    """Controlled encryption/decryption failure without leaking plaintext."""


class TokenValidationError(ValueError):
    """Raised when a JWT cannot be verified."""


_password_hasher = PasswordHasher()
_totp_interval_seconds = 30
_totp_digits = 6
_totp_issuer = "activia-trace"


def _get_key_bytes() -> bytes:
    return get_settings().encryption_key.encode("utf-8")


def encrypt_value(plaintext: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_get_key_bytes()).encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = urlsafe_b64encode(nonce + ciphertext).decode("utf-8")
    return f"v1:{payload}"


def decrypt_value(payload: str) -> str:
    try:
        version, encoded = payload.split(":", maxsplit=1)
        if version != "v1":
            raise EncryptionError("Encrypted payload is invalid")

        raw_payload = urlsafe_b64decode(encoded.encode("utf-8"))
        nonce = raw_payload[:12]
        ciphertext = raw_payload[12:]
        plaintext = AESGCM(_get_key_bytes()).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except (ValueError, UnicodeDecodeError, InvalidTag, binascii.Error) as exc:
        raise EncryptionError("Encrypted payload could not be decrypted") from exc


def hash_token(token: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hashlib.sha256(secret + token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(*, user_id: str, tenant_id: str, roles: list[str]) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise TokenValidationError("Access token is invalid") from exc


def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8").rstrip("=")


def _decode_totp_secret(secret: str) -> bytes:
    padding = "=" * (-len(secret) % 8)
    return base64.b32decode((secret + padding).encode("utf-8"), casefold=True)


def _totp_counter(now: datetime) -> int:
    return int(now.timestamp()) // _totp_interval_seconds


def generate_totp_code(secret: str, *, now: datetime | None = None) -> str:
    resolved_now = now or datetime.now(timezone.utc)
    counter = _totp_counter(resolved_now)
    counter_bytes = counter.to_bytes(8, byteorder="big")
    digest = hmac.new(_decode_totp_secret(secret), counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary_code = ((digest[offset] & 0x7F) << 24) | (digest[offset + 1] << 16) | (digest[offset + 2] << 8) | digest[offset + 3]
    return str(binary_code % (10**_totp_digits)).zfill(_totp_digits)


def verify_totp_code(secret: str, code: str, *, now: datetime | None = None) -> bool:
    resolved_now = now or datetime.now(timezone.utc)
    for offset in (-1, 0, 1):
        candidate_now = resolved_now + timedelta(seconds=offset * _totp_interval_seconds)
        if hmac.compare_digest(generate_totp_code(secret, now=candidate_now), code):
            return True
    return False


def build_totp_provisioning_uri(*, secret: str, account_name: str) -> str:
    encoded_label = quote(f"{_totp_issuer}:{account_name}")
    encoded_account = quote(account_name)
    return f"otpauth://totp/{encoded_label}?secret={secret}&issuer={_totp_issuer}&account={encoded_account}"
