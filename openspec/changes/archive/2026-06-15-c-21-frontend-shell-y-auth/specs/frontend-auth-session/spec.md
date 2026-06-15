## ADDED Requirements

### Requirement: Session store and identity derivation

The client SHALL maintain a session store holding the access token in memory and persisting the refresh token so the session survives a page reload. Identity (user id, tenant id, roles, expiration) SHALL be derived exclusively from the decoded JWT claims (`sub`, `tenant_id`, `roles`, `exp`). No value from any other source SHALL be treated as the user's identity. The client SHALL NOT make authorization decisions of record — the backend remains the source of truth and may return `403`.

#### Scenario: Identity comes from the JWT

- **WHEN** a session is established with an access token
- **THEN** the store exposes user id, tenant id, and roles read from the token's claims

#### Scenario: Session rehydrates after reload

- **WHEN** the app reloads and a persisted refresh token is present
- **THEN** the client restores the session by refreshing the access token

#### Scenario: Expired access without valid refresh is treated as no session

- **WHEN** the access token is expired and no valid refresh token is available
- **THEN** the store reports no active session

### Requirement: Login flow

The login page SHALL render a form (email, password, optional tenant) validated with React Hook Form and Zod, and submit to `POST /api/auth/login`. On a token response the session SHALL be established and the user navigated into the authenticated area. On a `requires_two_factor` response the user SHALL be routed to the 2FA challenge carrying the `challenge_token`. Loading and error states SHALL always be rendered.

#### Scenario: Login form renders

- **WHEN** an unauthenticated user opens `/login`
- **THEN** the email and password fields and a submit control are rendered

#### Scenario: Successful login establishes the session

- **WHEN** valid credentials are submitted and the backend returns access and refresh tokens
- **THEN** the session is established and the user is navigated into the authenticated area

#### Scenario: Invalid credentials show an error

- **WHEN** the backend returns an authentication error
- **THEN** the form shows an error message and no session is established

#### Scenario: 2FA-enabled account is routed to the challenge

- **WHEN** the backend responds with `requires_two_factor` and a `challenge_token`
- **THEN** the user is routed to the 2FA challenge with the `challenge_token` available

### Requirement: Two-factor login challenge

The 2FA challenge page SHALL accept a TOTP code and submit it together with the `challenge_token` to `POST /api/auth/2fa/verify-login`. On success the session SHALL be established from the returned tokens.

#### Scenario: Valid 2FA code establishes the session

- **WHEN** a correct TOTP code is submitted with a valid `challenge_token`
- **THEN** the backend returns tokens and the session is established

#### Scenario: Invalid 2FA code shows an error

- **WHEN** an incorrect code is submitted
- **THEN** an error is shown and no session is established

### Requirement: Password recovery flow

The recovery flow SHALL provide a "forgot password" form that submits an email to `POST /api/auth/forgot` and always shows a neutral confirmation (without revealing whether the email exists), and a "reset password" form that submits a token and new password to `POST /api/auth/reset`.

#### Scenario: Forgot password shows neutral confirmation

- **WHEN** an email is submitted to the forgot form
- **THEN** a neutral confirmation message is shown regardless of whether the account exists

#### Scenario: Reset password with a valid token

- **WHEN** a valid token and a new password are submitted
- **THEN** the password is reset and the user can proceed to log in

#### Scenario: Reset password with an invalid token

- **WHEN** the backend rejects the token
- **THEN** an error is shown and the password is not changed

### Requirement: Logout

The client SHALL provide a logout action that calls `POST /api/auth/logout` with the current refresh token, clears the local session (access in memory and persisted refresh token), and navigates to `/login`.

#### Scenario: Logout clears the session

- **WHEN** an authenticated user triggers logout
- **THEN** the client calls the logout endpoint, removes the stored tokens, and navigates to `/login`

#### Scenario: Logout clears the session even if the call fails

- **WHEN** the logout request fails
- **THEN** the local session is still cleared and the user is sent to `/login`

### Requirement: Route guard by session and role

The client SHALL provide a route guard that requires an active session for protected routes and redirects to `/login` when none exists. The guard SHALL optionally enforce a required role (or set of roles) read from the session and render a "no access" state when the role is missing. Fine-grained permission enforcement remains server-side.

#### Scenario: No session redirects to login

- **WHEN** an unauthenticated user requests a protected route
- **THEN** the guard redirects to `/login`

#### Scenario: Session without required role is blocked

- **WHEN** an authenticated user lacks a role required by a route
- **THEN** the guard renders a "no access" state instead of the route content

#### Scenario: Session with required role passes

- **WHEN** an authenticated user has the role required by a route
- **THEN** the guard renders the route content
