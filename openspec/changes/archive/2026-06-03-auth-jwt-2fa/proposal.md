## Why

C-03 establishes the authentication foundation required before RBAC, audit, and frontend auth can safely exist. It closes ADR-001 for the MVP: own email/password auth with short-lived JWT sessions, refresh rotation, optional TOTP 2FA, and password recovery, while preserving the non-negotiable rule that identity and tenant come only from a verified session.

## What Changes

- Add `POST /api/auth/login` using email + Argon2id password verification.
- Issue access JWTs valid for 15 minutes and refresh tokens with rotation.
- Invalidate a session when a used refresh token is reused.
- Include minimal JWT claims: `user_id`, `tenant_id`, `roles`, `exp`; do not include permissions.
- Add `POST /api/auth/refresh` and `POST /api/auth/logout`.
- Add optional per-user TOTP enrollment, verification, and login gating before session issuance.
- Add forgot/reset password flow with one-time short-lived reset tokens.
- Add login rate limiting of 5 attempts per 60 seconds per IP + email.
- Add `get_current_user` dependency that derives user identity and tenant only from a verified JWT.
- Keep fine permission catalog and `require_permission(...)` guards out of scope for C-04.

## Capabilities

### New Capabilities
- `auth-session`: Login, access JWT, refresh rotation, refresh reuse invalidation, logout, and session persistence/revocation.
- `auth-identity-context`: Verified-token identity resolution and the golden rule that request params/body/headers cannot override user or tenant.
- `auth-totp-2fa`: Optional TOTP enrollment, verification, and session issuance gate.
- `auth-password-recovery`: Forgot/reset password with short-lived one-time tokens.
- `auth-login-rate-limit`: Login throttling per IP + normalized email.

### Modified Capabilities
- None. C-02 tenant-scoped repository and core tenant requirements remain unchanged and are consumed as prerequisites.

## Impact

- Backend auth API under `backend/app/api/v1/routers/auth.py`.
- Security and DI modules under `backend/app/core/security.py` and `backend/app/core/dependencies.py`.
- Auth schemas, services, repositories, and models for users, sessions, 2FA secrets, and reset tokens.
- Alembic migration after `001_tenant` for auth tables.
- Tests covering login OK/KO, refresh rotation/reuse invalidation, 2FA, recovery one-time token, rate limit, and identity immutability.
- External email delivery for recovery is planned behind a service boundary; actual provider wiring may be deferred or stubbed for this backend change.
