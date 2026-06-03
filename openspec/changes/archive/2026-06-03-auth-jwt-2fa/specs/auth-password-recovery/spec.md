## ADDED Requirements

### Requirement: Forgot password creates a short-lived one-time token
The system SHALL expose `POST /api/auth/forgot` for anonymous password recovery requests. For an active user email, the system MUST create a short-lived reset token that can be used only once and is stored only as a secure hash.

#### Scenario: Forgot password accepts existing email without exposing token hash
- **WHEN** an active user requests password recovery for their email
- **THEN** the system creates a short-lived reset token record for that user
- **AND** the persisted token representation is not the plaintext token
- **AND** the token can be delivered through the configured recovery delivery boundary

#### Scenario: Forgot password response does not enumerate users
- **WHEN** a recovery request is submitted for an email with no active user
- **THEN** the system returns the same safe acknowledgement used for existing users
- **AND** no response data reveals whether the email exists

### Requirement: Reset password consumes token and updates Argon2id password hash
The system SHALL expose `POST /api/auth/reset` to accept a valid reset token and new password. A successful reset MUST update the user's password hash using Argon2id and consume the token.

#### Scenario: Valid reset token updates password once
- **WHEN** a user submits a valid unexpired reset token with a new acceptable password
- **THEN** the system updates the user's stored password hash using Argon2id
- **AND** the reset token is marked consumed
- **AND** the plaintext password is never stored

#### Scenario: Consumed reset token cannot be reused
- **WHEN** a reset token has already been used successfully
- **THEN** a later reset attempt with the same token is rejected
- **AND** the user's password is not changed by the later attempt

#### Scenario: Expired reset token is rejected
- **WHEN** a user submits an expired reset token
- **THEN** the system rejects the reset request
- **AND** the user's password hash remains unchanged

### Requirement: Password reset invalidates active refresh sessions
The system MUST revoke existing refresh sessions for the user after a successful password reset.

#### Scenario: Old refresh token fails after password reset
- **WHEN** a user's password is reset successfully
- **THEN** refresh sessions issued before the reset are revoked
- **AND** previously issued refresh tokens for that user cannot be used to obtain new access tokens
