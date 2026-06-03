# auth-session Specification

## Purpose
TBD - created by archiving change auth-jwt-2fa. Update Purpose after archive.
## Requirements
### Requirement: Login validates tenant user credentials with Argon2id
The system SHALL expose `POST /api/auth/login` for anonymous email and password authentication. Password verification MUST use Argon2id against the stored password hash, and successful credential validation MUST resolve exactly one tenant-owned active user.

#### Scenario: Login succeeds with valid credentials and no 2FA gate
- **WHEN** an active tenant user submits the correct email and password and 2FA is not enabled for that user
- **THEN** the system returns an access token and refresh token
- **AND** the access token expires in 15 minutes
- **AND** the access token contains `user_id`, `tenant_id`, `roles`, and `exp`

#### Scenario: Login fails with invalid password
- **WHEN** a login request submits an existing email with an incorrect password
- **THEN** the system rejects the request with an authentication failure
- **AND** no access token or refresh token is issued

#### Scenario: Login fails for inactive or missing user
- **WHEN** a login request submits an email that has no active tenant user
- **THEN** the system rejects the request with the same generic authentication failure used for invalid credentials
- **AND** the response does not reveal whether the email exists

### Requirement: Refresh token rotation issues a new token pair
The system SHALL expose `POST /api/auth/refresh` to exchange a valid refresh token for a new access token and a new refresh token. The presented refresh token MUST be invalidated as part of the successful exchange.

#### Scenario: Refresh succeeds and rotates token
- **WHEN** a client submits a valid, unexpired, unused refresh token
- **THEN** the system invalidates the presented refresh token
- **AND** the system returns a new access token and a new refresh token
- **AND** the new access token preserves the verified `user_id`, `tenant_id`, and `roles` from the session owner

#### Scenario: Old refresh token cannot be reused after rotation
- **WHEN** a refresh token has already been exchanged successfully
- **THEN** a later request using that same refresh token is rejected
- **AND** no new token pair is issued

### Requirement: Refresh reuse invalidates the session family
The system MUST treat reuse of an already used, revoked, or replaced refresh token as a session compromise signal and invalidate the associated refresh token family/session.

#### Scenario: Reused refresh revokes descendant session tokens
- **WHEN** a previously used refresh token is presented after rotation
- **THEN** the system revokes the associated refresh token family/session
- **AND** any descendant refresh token from that family can no longer be used to obtain tokens

### Requirement: Logout revokes the authenticated session
The system SHALL expose `POST /api/auth/logout` to revoke the current refresh session. Logout MUST make the active refresh token unusable for future refresh requests.

#### Scenario: Logout revokes refresh token
- **WHEN** an authenticated user logs out for the current session
- **THEN** the system marks the current refresh token/session as revoked
- **AND** a subsequent refresh using that token is rejected

### Requirement: Access token permissions are excluded
The system MUST NOT include fine-grained permissions in access JWT claims. Permission catalog and permission guard behavior are reserved for C-04.

#### Scenario: Access token contains roles but no permissions
- **WHEN** the system issues an access token after successful authentication
- **THEN** the token contains role identifiers for the user
- **AND** the token does not contain `permissions`, `permission_catalog`, or equivalent fine-grained authorization data

