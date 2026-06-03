# auth-login-rate-limit Specification

## Purpose
TBD - created by archiving change auth-jwt-2fa. Update Purpose after archive.
## Requirements
### Requirement: Login attempts are rate limited per IP and email
The system SHALL enforce a login rate limit of 5 attempts per 60 seconds for each client IP and normalized email combination.

#### Scenario: Sixth login attempt within window is rejected
- **WHEN** the same client IP and normalized email combination submits 5 login attempts within 60 seconds
- **THEN** the sixth login attempt in that window is rejected with a rate-limit response
- **AND** no credential verification result or token is returned for the rejected attempt

#### Scenario: Different email or IP has independent limit bucket
- **WHEN** one IP and email combination reaches the login limit
- **THEN** a login attempt for a different normalized email or from a different IP uses a separate limit bucket

#### Scenario: Limit window reset allows a later attempt
- **WHEN** the 60-second rate-limit window has elapsed for an IP and normalized email combination
- **THEN** a new login attempt for that combination is evaluated normally

### Requirement: Rate limit does not leak account existence
The system MUST apply login throttling and responses in a way that does not reveal whether the submitted email belongs to an active user.

#### Scenario: Unknown email receives same rate-limit behavior
- **WHEN** repeated login attempts are made for an unknown email from the same IP
- **THEN** the same 5 per 60 seconds limit is enforced
- **AND** rate-limit responses do not reveal whether the email exists

