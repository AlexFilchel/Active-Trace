## ADDED Requirements

### Requirement: TOTP enrollment creates a verifiable secret without enabling 2FA prematurely
The system SHALL allow an authenticated user to begin TOTP enrollment by generating a TOTP secret and provisioning data. The system MUST NOT mark 2FA as enabled until a valid TOTP code verifies the enrollment.

#### Scenario: Enrollment starts in pending state
- **WHEN** an authenticated user requests TOTP enrollment
- **THEN** the system creates or replaces a pending encrypted TOTP secret for that user
- **AND** the user is not considered 2FA-enabled until verification succeeds

#### Scenario: Enrollment verification enables 2FA
- **WHEN** the user submits a valid TOTP code for the pending enrollment secret
- **THEN** the system marks TOTP 2FA as enabled for that user
- **AND** future password logins for that user require TOTP verification before session issuance

### Requirement: 2FA-enabled users are gated before session issuance
The system MUST require a successful TOTP verification after valid password credentials and before issuing access or refresh tokens for users with enabled 2FA.

#### Scenario: Login returns pending challenge for 2FA user
- **WHEN** a user with enabled TOTP submits valid email and password credentials
- **THEN** the system returns a short-lived pending 2FA challenge instead of access and refresh tokens
- **AND** no authenticated session is issued yet

#### Scenario: Valid TOTP challenge issues session
- **WHEN** the user submits a valid TOTP code for an active pending challenge
- **THEN** the system consumes the challenge
- **AND** the system issues an access token and refresh token for that user session

#### Scenario: Invalid TOTP code blocks session
- **WHEN** the user submits an invalid TOTP code for a pending challenge
- **THEN** the system rejects the verification
- **AND** no access token or refresh token is issued

### Requirement: TOTP secrets are protected at rest
The system MUST store TOTP secrets encrypted at rest using the C-02 AES-256 encryption utility or an equivalent AES-256 protected representation.

#### Scenario: Persisted TOTP secret is not plaintext
- **WHEN** a TOTP secret is persisted for enrollment or enabled 2FA
- **THEN** the stored value differs from the plaintext secret
- **AND** the plaintext secret is not exposed in logs or normal API responses after enrollment provisioning
