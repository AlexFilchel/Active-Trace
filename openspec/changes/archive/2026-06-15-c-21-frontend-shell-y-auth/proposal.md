## Why

El backend de activia-trace ya expone autenticación completa (login, 2FA TOTP, refresh con rotación, recuperación de contraseña, logout) y RBAC fino, pero todavía no existe un frontend. Sin un shell de React con un cliente HTTP centralizado que maneje el ciclo de vida de la sesión (access token de 15 min + refresh transparente) y guards de ruta por permiso, ninguna funcionalidad de la plataforma es operable por un usuario real. C-21 establece ese cimiento: el scaffold de la SPA y el flujo de autenticación end-to-end (FL-01), del que dependen todas las pantallas posteriores.

## What Changes

- **Scaffold de la SPA**: proyecto React 18 + TypeScript + Vite con estructura feature-based (`features/{name}/{components,hooks,services,types,pages}` + `shared/`), Tailwind CSS, TanStack Query, React Hook Form + Zod y Axios. Sin `any`, sin class components, componentes <200 LOC.
- **Cliente HTTP centralizado** (`shared/services/api`): instancia Axios única con interceptor de request que inyecta el `Authorization: Bearer <access_token>` y un interceptor de response que, ante un `401`, dispara **refresh transparente** del token (una sola request de refresh concurrente; las peticiones en vuelo se reencolan y se reintentan), y ante un `403` propaga un error de autorización sin reintentar.
- **Gestión de sesión en cliente**: store de sesión (access token en memoria, refresh token persistido de forma controlada) con derivación de identidad (user id, tenant, roles) desde los claims del JWT — la sesión es la única fuente de identidad en el cliente; la autorización real siempre la decide el backend.
- **Pantallas de autenticación** que consumen los endpoints de C-03: login (email + password + tenant opcional), challenge de **2FA** (verify-login con `challenge_token`), recuperación de contraseña (forgot + reset) y logout. Estados de loading y error siempre presentes.
- **Guard de rutas por permiso**: componente que protege rutas exigiendo sesión válida y, opcionalmente, un permiso/rol; redirige a login cuando no hay sesión y a una pantalla de "sin acceso" cuando falta el permiso.
- **Layout y menú adaptados a la sesión**: shell con navegación cuyas entradas se muestran/ocultan según los roles/permisos efectivos de la sesión.

## Capabilities

### New Capabilities
- `frontend-app-shell`: scaffold de la SPA (estructura feature-based, Tailwind, TanStack Query, RHF+Zod, Axios), layout raíz, router con rutas públicas/privadas y menú adaptado a la sesión.
- `frontend-http-client`: cliente Axios centralizado con interceptores de auth y refresh transparente de tokens, y mapeo uniforme de errores 401/403.
- `frontend-auth-session`: store y ciclo de vida de la sesión en el cliente (login, 2FA, recuperación de contraseña, logout, persistencia y derivación de identidad desde el JWT) y guard de rutas por sesión/permiso.

### Modified Capabilities
<!-- Ninguna: C-21 no cambia requisitos de specs backend existentes; solo las consume. -->

## Impact

- **Nuevo directorio `frontend/`** creado desde cero (no existía). Tooling: Vite, TypeScript, Tailwind, Vitest + Testing Library para tests de componentes/flujo.
- **Consume contratos backend de C-03** (sin modificarlos): `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `POST /api/auth/2fa/verify-login`, `POST /api/auth/forgot`, `POST /api/auth/reset`. Lee perfil vía `GET /api/perfil`.
- **Depende de C-04 (RBAC backend)** para la semántica de permisos que el guard y el menú reflejan.
- **Sin impacto en backend ni base de datos.** Governance del dominio: BAJO (frontend shell sin lógica crítica de seguridad server-side).
- **Open question (PA-FE-01)**: el JWT lleva `roles` pero NO el set de permisos efectivos (se resuelven server-side por request) y ningún endpoint actual los expone al cliente. El guard de C-21 se basa en roles del JWT como hint de UI; la autorización fina sigue siendo server-side. Si se requiere guard por permiso fino en cliente, hace falta un endpoint `/api/auth/me` (o equivalente) que devuelva los permisos efectivos — se documenta como decisión en design.md.
