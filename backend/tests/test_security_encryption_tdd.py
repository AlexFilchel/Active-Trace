import pytest

from app.core import security


def test_encrypt_and_decrypt_round_trip(valid_env):
    plaintext = "12345678"

    ciphertext = security.encrypt_value(plaintext)

    assert security.decrypt_value(ciphertext) == plaintext


def test_ciphertext_differs_from_plaintext(valid_env):
    plaintext = "dni-20-12345678-9"

    ciphertext = security.encrypt_value(plaintext)

    assert ciphertext != plaintext


def test_decrypt_fails_with_wrong_key(valid_env, monkeypatch: pytest.MonkeyPatch):
    plaintext = "sensitive@example.com"
    ciphertext = security.encrypt_value(plaintext)

    monkeypatch.setenv("ENCRYPTION_KEY", "x" * 32)
    security.get_settings.cache_clear()

    with pytest.raises(Exception):
        security.decrypt_value(ciphertext)


def test_decrypt_rejects_invalid_payload(valid_env):
    with pytest.raises(Exception):
        security.decrypt_value("not-a-valid-payload")


def test_encrypt_and_decrypt_support_empty_and_unicode_values(valid_env):
    values = ["", "áéíóú 👩🏽‍💻"]

    for plaintext in values:
        ciphertext = security.encrypt_value(plaintext)

        assert security.decrypt_value(ciphertext) == plaintext


def test_encryption_errors_do_not_echo_plaintext(valid_env, monkeypatch: pytest.MonkeyPatch):
    plaintext = "dni-super-secreto-123"
    ciphertext = security.encrypt_value(plaintext)

    monkeypatch.setenv("ENCRYPTION_KEY", "z" * 32)
    security.get_settings.cache_clear()

    with pytest.raises(security.EncryptionError) as exc_info:
        security.decrypt_value(ciphertext)

    assert plaintext not in str(exc_info.value)
