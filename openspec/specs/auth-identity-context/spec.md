# auth-identity-context Specification

## Purpose
TBD - created by archiving change auth-jwt-2fa. Update Purpose after archive.
## Requirements
### Requirement: Current user is resolved only from a verified JWT
The system SHALL provide a `get_current_user` dependency that verifies the access JWT signature and expiration, then resolves the current user identity, tenant, and roles from the verified token claims only.

#### Scenario: Valid access token resolves current identity
- **WHEN** a request includes a valid access JWT
- **THEN** `get_current_user` returns the `user_id`, `tenant_id`, and `roles` from the verified token
- **AND** the returned tenant context can be passed to tenant-scoped repositories

#### Scenario: Missing or invalid token is rejected
- **WHEN** a request has no access JWT or has a token with invalid signature or expiration
- **THEN** the dependency rejects the request as unauthenticated
- **AND** no tenant context is created from request data

### Requirement: Request data cannot override authenticated identity
The system MUST ignore query parameters, path parameters, request body fields, and arbitrary headers as sources of authenticated `user_id`, `tenant_id`, or roles. Such values MAY be treated only as business input validated against the current authenticated context.

#### Scenario: Tenant query parameter cannot override token tenant
- **WHEN** a request includes a valid JWT for tenant A and also sends `tenant_id` for tenant B in query parameters or body
- **THEN** the current tenant remains tenant A from the verified JWT
- **AND** tenant-scoped repository operations use tenant A

#### Scenario: User parameter cannot impersonate another identity
- **WHEN** a request includes a valid JWT for user A and also sends `user_id` for user B in path, query, body, or headers
- **THEN** the current user remains user A from the verified JWT
- **AND** the request data does not alter the authenticated actor

### Requirement: Tenant context preserves C-02 repository isolation
The system SHALL construct repository tenant context from the verified JWT tenant and MUST preserve the C-02 fail-closed repository contract.

#### Scenario: Authenticated tenant context scopes repository access
- **WHEN** an authenticated request executes a tenant-owned repository operation through application dependencies
- **THEN** the repository receives the tenant identifier from the verified JWT
- **AND** rows from other tenants remain inaccessible by default

