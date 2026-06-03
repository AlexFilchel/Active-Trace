from functools import lru_cache

from pydantic import Field, field_validator
from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        populate_by_name=True,
    )

    database_url: PostgresDsn = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    encryption_key: str = Field(alias="ENCRYPTION_KEY")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="activia-trace-api", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must have at least 32 characters")
        return value

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        if len(value) != 32:
            raise ValueError("ENCRYPTION_KEY must be exactly 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
