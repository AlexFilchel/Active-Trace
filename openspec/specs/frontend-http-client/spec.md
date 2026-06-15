## ADDED Requirements

### Requirement: Centralized Axios client

All HTTP communication with the backend SHALL go through a single Axios instance exported from `shared/services/api`. Feature services MUST use this instance and MUST NOT create their own Axios instances or call `fetch` directly. The instance SHALL be configured with the API base URL and JSON defaults.

#### Scenario: Single shared instance is used

- **WHEN** any feature service issues a request
- **THEN** it uses the shared Axios instance from `shared/services/api`

### Requirement: Authorization header injection

The client SHALL attach an `Authorization: Bearer <access_token>` header to every outgoing request when an access token is present in the session. Requests to public auth endpoints (`/auth/login`, `/auth/refresh`, `/auth/forgot`, `/auth/reset`) SHALL NOT require an access token.

#### Scenario: Authenticated request carries the bearer token

- **WHEN** a session with an access token is active and a request is sent
- **THEN** the request includes the header `Authorization: Bearer <access_token>`

#### Scenario: No token, no header

- **WHEN** no session is active and a request is sent to a public endpoint
- **THEN** the request is sent without an `Authorization` header

### Requirement: Transparent token refresh on 401

When a request to a protected endpoint receives a `401`, the client SHALL transparently attempt a token refresh via `POST /api/auth/refresh` using the stored refresh token, then retry the original request exactly once with the new access token. Concurrent `401` responses SHALL share a single in-flight refresh (no more than one refresh request is issued at a time) and all queued requests SHALL be retried with the refreshed token. A request that already retried once MUST NOT trigger another refresh.

#### Scenario: Expired access token is refreshed and the request retried

- **WHEN** a protected request returns `401` and a valid refresh token is available
- **THEN** the client calls `/api/auth/refresh`, stores the rotated tokens, and retries the original request once, which then succeeds

#### Scenario: Concurrent 401s share one refresh

- **WHEN** multiple protected requests return `401` at the same time
- **THEN** exactly one `/api/auth/refresh` call is made and every original request is retried with the new access token

#### Scenario: Refresh failure clears the session

- **WHEN** the `/api/auth/refresh` call itself returns `401` or an invalid response
- **THEN** the client clears the session and redirects to `/login`, and the queued requests are rejected

#### Scenario: No refresh loop after a failed retry

- **WHEN** a request that was already retried once returns `401` again
- **THEN** the client does NOT attempt another refresh and the session is cleared

### Requirement: Authorization error handling on 403

When a request receives a `403`, the client SHALL surface an authorization error to the caller WITHOUT attempting a token refresh or retry.

#### Scenario: Forbidden response is not retried

- **WHEN** a protected request returns `403`
- **THEN** the client propagates an authorization error and does not call `/api/auth/refresh`
