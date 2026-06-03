import pytest
from pydantic import ValidationError


def test_settings_loads_with_valid_environment(valid_env):
    from app.core.config import Settings

    settings = Settings()

    assert settings.database_url.unicode_string().startswith("postgresql+asyncpg://")
    assert settings.access_token_expire_minutes == 15


def test_settings_fails_when_required_value_is_missing(monkeypatch, valid_env):
    from app.core.config import Settings

    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "SECRET_KEY" in str(exc_info.value)


def test_settings_fails_when_value_type_is_invalid(monkeypatch, valid_env):
    from app.core.config import Settings

    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "fifteen")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "ACCESS_TOKEN_EXPIRE_MINUTES" in str(exc_info.value)


def test_settings_fails_when_database_url_is_invalid(invalid_db_url_env):
    from app.core.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "DATABASE_URL" in str(exc_info.value)
