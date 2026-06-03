## Context

`auth-jwt-2fa` is CRITICAL governance planning for C-03. C-01 provides FastAPI, DB, config, logging and pytest; C-02 provides `Tenant`, lifecycle mixins, AES-256 helper, and tenant-scoped repository conventions. Current `core/dependencies.py` reserves `get_current_user` for this change, and `core/security.py` currently contains only encryption.

The change must implement ADR-001: own auth for MVP with email/password, Argon2id, TOTP, 15-minute access JWTs, and rotating refresh tokens. The golden rule is an invariant: user identity, roles, and tenant are resolved from a verified JWT only.

## Goals / Non-Goals

**Goals:**
- Provide anonymous auth endpoints only for login, refresh, logout, 2FA challenge/enrollment verification, forgot, and reset.
- Persist users, refresh sessions, TOTP secrets, and reset tokens with tenant scoping where applicable.
- Expose `get_current_user` / tenant context for downstream repositories.
- Enforce refresh rotation, reuse detection, login rate limit, and one-time recovery tokens.
- Cover behavior with Strict TDD and real DB/integration tests.

**Non-Goals:**
- No C-04 permission catalog, `require_permission(...)`, or endpoint permission matrix.
- No frontend implementation; C-21 consumes these endpoints later.
- No Moodle SSO; ADR-001 defers it beyond MVP auth.
- No impersonation implementation; ADR-004 is deferred.

## Decisions

### 1. Session model and refresh rotation

Persist refresh token family/session rows with hashed refresh tokens, `user_id`, `tenant_id`, expiration, revoked timestamps, and replacement linkage. On refresh, mark the presented token used/revoked and issue a new pair. If a previously used/revoked token is presented again, revoke the whole token family/session.

**Rationale:** Enables reuse detection without storing plaintext refresh tokens. Alternative considered: stateless refresh JWT only; rejected because reuse invalidation and logout become unreliable.

### 2. Access JWT content

Access JWTs carry only `user_id`, `tenant_id`, `roles`, and `exp` (implementation may map `user_id` to `sub` internally only if response/verification normalizes to the required claim contract). No permissions are encoded.

**Rationale:** Preserves C-04 separation and prevents stale authorization. Alternative considered: embedding permissions; rejected because RBAC catalog is C-04 and must resolve server-side.

### 3. Auth boundaries by layer

Routers validate HTTP and call services. Services orchestrate credential checks, token generation, 2FA gates, and recovery. Repositories perform all SQL. `core/security.py` owns crypto primitives: Argon2id verification/hash, JWT sign/verify, secure token hashing, TOTP helpers, and existing AES utility.

**Rationale:** Matches hard Clean Architecture rules. Alternative: direct DB in dependencies; rejected except for dependency-injected repository calls inside the dependency resolver.

### 4. 2FA gate before session issuance

If a user has TOTP enabled, password validation returns a short-lived, single-purpose pending auth challenge instead of tokens. Only a valid TOTP verification completes login and issues the session.

**Rationale:** FL-01 requires second factor before session issuance. Alternative: issue access token with `mfa_pending`; rejected because it creates an authenticated session before second factor.

### 5. Recovery tokens and emails

Forgot password creates a short-lived one-time token stored only as a hash. Email delivery is behind a service boundary so tests can assert token lifecycle without an external provider.

**Rationale:** Keeps C-03 backend deterministic and avoids coupling to N8N/mail provider before communication changes. Alternative: inline provider call; rejected for testability and roadmap separation.

### 6. Login rate limit scope

Rate limit key is normalized email + client IP. It applies before expensive Argon2 verification when possible and returns a safe generic auth failure shape.

**Rationale:** Mitigates brute force while not leaking whether an email exists. Alternative: per user id; rejected because anonymous login has no verified user yet.

## Risks / Trade-offs

- [User model timing] C-07 later expands `Usuario`; C-03 needs a minimal auth user table now → Keep fields minimal and tenant-scoped, and document later extension/merge in C-07.
- [Secret handling] TOTP secrets and reset/refresh material are sensitive → Store TOTP secret encrypted with AES-256 and tokens only as hashes.
- [Rate limit persistence] In-memory rate limits are simple but per-process → For MVP tests use an injectable limiter; document that distributed deployment should move to Redis/shared storage.
- [2FA recovery UX] Backup codes are not in roadmap scope → Caveat as future enhancement, not part of C-03 acceptance.

## Migration Plan

1. Add a single sequential Alembic migration after `001_tenant` for auth schema.
2. Create minimal tenant-owned auth user/session/2FA/reset-token tables with soft delete/lifecycle conventions where applicable.
3. Add auth services, repositories, schemas, routes, and dependencies.
4. Register auth router in FastAPI.
5. Run Strict TDD test suites for auth and existing tenant/security tests.

**Rollback:** Downgrade the auth migration to remove C-03 tables and remove auth router registration. Existing C-01/C-02 tables and specs remain unaffected.

## Open Questions

- Exact email delivery provider for recovery tokens is deferred; implementation should use an interface/test double and avoid hard provider dependencies.
- Distributed rate limit backend is not specified; implementation should keep a pluggable boundary so Redis/shared storage can replace local memory later.
