## 1. Safety Net and Auth Data Model

- [x] 1.1 Run existing C-01/C-02 backend tests as the safety net and report any pre-existing failures before code changes.
- [x] 1.2 Add RED tests for auth schema migration: auth users, refresh sessions/families, TOTP secrets/challenges, reset tokens, indexes, lifecycle fields, and tenant foreign keys.
- [x] 1.3 Implement the single sequential Alembic auth migration after `001_tenant` and ORM models using C-02 lifecycle/tenant conventions.
- [x] 1.4 Add repository tests proving auth entities are tenant-scoped, soft-deleted records are excluded by default, and token records never persist plaintext token values.
- [x] 1.5 Implement auth repositories only after the repository tests fail.

## 2. Security Primitives

- [x] 2.1 Add RED unit tests for Argon2id password hashing/verification, JWT sign/verify with 15-minute expiry, secure random token hashing, and invalid-token failures.
- [x] 2.2 Implement password, JWT, and token-hash helpers in `backend/app/core/security.py` with no plaintext secret logging.
- [x] 2.3 Add RED tests for TOTP generation/verification and AES-256 encrypted TOTP secret persistence.
- [x] 2.4 Implement TOTP helper functions and encrypted secret handling.

## 3. Login, Session Issuance, Refresh, and Logout

- [x] 3.1 Add RED API/service tests for login success, invalid password, missing/inactive user, minimal JWT claims, and absence of permission claims.
- [x] 3.2 Implement auth schemas with Pydantic v2 `extra='forbid'`, auth service credential validation, and `POST /api/auth/login` without 2FA enabled.
- [x] 3.3 Add RED tests for refresh rotation: valid refresh returns a new pair and invalidates the old token.
- [x] 3.4 Implement refresh token rotation and session/family persistence.
- [x] 3.5 Add RED tests for refresh-token reuse invalidating descendant session tokens.
- [x] 3.6 Implement reuse detection and family/session revocation.
- [x] 3.7 Add RED tests for logout revoking the current refresh token/session.
- [x] 3.8 Implement `POST /api/auth/logout`.

## 4. Current User and Golden Rule

- [x] 4.1 Add RED dependency tests for valid JWT identity resolution and invalid/missing token rejection.
- [x] 4.2 Implement `get_current_user` and tenant context construction from verified JWT claims only.
- [x] 4.3 Add RED tests proving `tenant_id`, `user_id`, and roles from path/query/body/headers cannot override the JWT identity.
- [x] 4.4 Wire authenticated tenant context into repository usage while preserving the C-02 fail-closed tenant-scoped repository contract.

## 5. Optional TOTP 2FA

- [x] 5.1 Add RED tests for TOTP enrollment pending state and successful verification enabling 2FA.
- [x] 5.2 Implement enrollment and verification service methods/endpoints.
- [x] 5.3 Add RED tests showing password login for a 2FA-enabled user returns a pending challenge and no session tokens.
- [x] 5.4 Implement pending 2FA challenge creation after password validation.
- [x] 5.5 Add RED tests showing valid TOTP consumes the challenge and issues a session, while invalid TOTP issues no tokens.
- [x] 5.6 Implement TOTP challenge verification and session issuance.

## 6. Password Recovery

- [x] 6.1 Add RED tests for forgot-password creating a short-lived hashed one-time token and using a non-enumerating response for known/unknown emails.
- [x] 6.2 Implement forgot-password service and `POST /api/auth/forgot` with delivery behind an injectable boundary.
- [x] 6.3 Add RED tests for reset-password updating an Argon2id hash, consuming the token, rejecting reused/expired tokens, and never storing plaintext passwords.
- [x] 6.4 Implement `POST /api/auth/reset`.
- [x] 6.5 Add RED tests proving successful password reset revokes existing refresh sessions.
- [x] 6.6 Implement refresh-session revocation on password reset.

## 7. Login Rate Limiting

- [x] 7.1 Add RED tests for 5 login attempts per 60 seconds per IP + normalized email, independent buckets, and post-window retry.
- [x] 7.2 Implement an injectable login rate limiter boundary and apply it before credential result disclosure.
- [x] 7.3 Add RED tests proving unknown emails receive the same throttling behavior and do not leak account existence.
- [x] 7.4 Implement non-enumerating rate-limit/error responses.

## 8. Integration, Regression, and Documentation Checks

- [x] 8.1 Register auth routes under the existing API router structure and add end-to-end API tests for login → refresh → logout.
- [x] 8.2 Run full backend tests and capture Strict TDD evidence for each task group.
- [x] 8.3 Verify OpenSpec scenarios map to tests: login OK/KO, refresh rotation/reuse invalidation, 2FA flow, recovery one-time token, rate limit, and identity immutability.
- [x] 8.4 Document any deferred provider choices or distributed rate-limit caveats discovered during implementation.
