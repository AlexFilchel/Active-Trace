from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictSchema):
    email: str
    password: str
    tenant_slug: str | None = None


class RefreshRequest(StrictSchema):
    refresh_token: str


class LogoutRequest(StrictSchema):
    refresh_token: str


class TotpVerifyRequest(StrictSchema):
    code: str


class LoginChallengeVerifyRequest(StrictSchema):
    challenge_token: str
    code: str


class ForgotPasswordRequest(StrictSchema):
    email: str


class ResetPasswordRequest(StrictSchema):
    token: str
    new_password: str
