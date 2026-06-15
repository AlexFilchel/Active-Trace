## ADDED Requirements

### Requirement: SPA scaffold with feature-based structure

The frontend SHALL be a React 18 + TypeScript Single Page Application built with Vite, organized in a feature-based module structure (`features/{name}/{components,hooks,services,types,pages}`) plus a `shared/` area for cross-cutting code. The build SHALL configure Tailwind CSS, TanStack Query, React Hook Form with Zod, and Axios. Components MUST be function components in PascalCase files, MUST NOT use `any`, MUST NOT use class components, and SHALL stay under 200 lines.

#### Scenario: Project builds and renders the root app

- **WHEN** the SPA is started in development
- **THEN** Vite serves the application and the root `App` component renders without runtime errors

#### Scenario: Feature-based directories exist

- **WHEN** the repository is inspected after scaffold
- **THEN** an `auth` feature exists under `features/auth/` with `components`, `hooks`, `services`, `types`, and `pages`, and a `shared/services/api` module exists

#### Scenario: TanStack Query provider wraps the app

- **WHEN** the application mounts
- **THEN** a single `QueryClientProvider` is present at the root so any feature hook can use server-state queries

### Requirement: Router with public and private routes

The application SHALL define public routes (`/login`, `/2fa`, `/forgot`, `/reset`) and private routes served under an authenticated layout. Private routes MUST be wrapped by a route guard that requires a valid session. Page components SHALL be lazy-loaded.

#### Scenario: Unknown private route requires session

- **WHEN** an unauthenticated user navigates to a private route
- **THEN** the guard redirects them to `/login`

#### Scenario: Public routes render without a session

- **WHEN** an unauthenticated user navigates to `/login`
- **THEN** the login page renders without redirecting

### Requirement: Layout and menu adapt to the session

The authenticated layout SHALL render a navigation menu whose entries are shown or hidden according to the roles present in the current session. The layout SHALL provide a visible action to log out.

#### Scenario: Menu reflects session roles

- **WHEN** the session contains a given set of roles
- **THEN** only the menu entries permitted for those roles are rendered

#### Scenario: Logout action is available when authenticated

- **WHEN** a user has an active session and views the authenticated layout
- **THEN** a logout control is visible and triggers the logout flow
