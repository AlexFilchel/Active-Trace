## Context

activia-trace tiene backend de auth y RBAC operativos pero ningún frontend. C-21 crea el directorio `frontend/` desde cero y entrega el shell de la SPA más el flujo de autenticación FL-01 (login, 2FA, recuperación, logout) con refresh transparente de tokens.

**Estado actual relevante (contratos backend C-03 verificados en código):**

- `POST /api/auth/login` — body `{ email, password, tenant_slug? }`. Respuesta:
  - sin 2FA → `{ access_token, refresh_token, token_type: "bearer" }`
  - con 2FA → `{ requires_two_factor: true, challenge_token, expires_in: 300 }`
- `POST /api/auth/2fa/verify-login` — body `{ challenge_token, code }` → `{ access_token, refresh_token, token_type }`
- `POST /api/auth/refresh` — body `{ refresh_token }` → `{ access_token, refresh_token, token_type }` (rotación: el refresh usado se invalida)
- `POST /api/auth/logout` — body `{ refresh_token }`, requiere `Authorization` → `204 No Content`
- `POST /api/auth/forgot` — body `{ email }` → `202 Accepted` (respuesta neutra, no revela si el email existe)
- `POST /api/auth/reset` — body `{ token, new_password }` → `200`
- `GET /api/perfil` — requiere `Authorization` → datos de perfil (no incluye permisos)

**Claims del JWT (verificado en `core/security`):** `sub` (user id), `tenant_id`, `roles`, `exp`. **No lleva permisos** — se resuelven server-side por request.

**Constraints del proyecto:** React 18 + TS (sin `any`, sin class components), Vite, TanStack Query (todo fetch vía hooks de `services/`), React Hook Form + Zod, Tailwind (sin CSS modules ni inline salvo valores dinámicos), Axios centralizado en `shared/services/api`, componentes <200 LOC, estructura feature-based, tests sin DB real (mocks de red). Strict TDD.

## Goals / Non-Goals

**Goals:**

- Scaffold de la SPA productivo (Vite + TS + Tailwind + TanStack Query + RHF/Zod + Axios) con estructura feature-based y `shared/`.
- Cliente HTTP único con interceptores: inyección de `Bearer` y **refresh transparente** ante 401 con dedupe de refresh concurrente y reencolado de requests en vuelo.
- Flujo de auth completo en UI: login, challenge 2FA, forgot/reset, logout. Loading + error states siempre.
- Guard de rutas: redirige a `/login` sin sesión; bloquea por permiso/rol cuando se exige uno.
- Layout con menú adaptado a la sesión (roles del JWT).
- Cobertura de tests del flujo crítico: render de login, login feliz (mock), guard sin sesión redirige, refresh transparente reintenta y no entra en loop.

**Non-Goals:**

- Implementar pantallas de dominio (calificaciones, comisiones, liquidaciones, etc.) — son changes posteriores.
- Enrollment de 2FA (`/2fa/enroll`, `/2fa/verify-enrollment`) y la UI de impersonación — fuera del MVP de C-21 (se consumen `verify-login`, no el setup).
- Guard por **permiso fino** en cliente (depende de un endpoint que hoy no existe — ver Open Questions). C-21 hace guard por sesión + rol.
- Cualquier cambio en backend o base de datos.

## Decisions

### D1 — Almacenamiento de tokens: access en memoria, refresh en `localStorage`

El **access token vive solo en memoria** (módulo del store de sesión); no se persiste. El **refresh token se persiste en `localStorage`** para sobrevivir recargas de página y permitir rehidratar la sesión al arrancar la app.

- **Por qué:** el access dura 15 min; mantenerlo en memoria minimiza superficie de XSS-exfiltración persistente. El refresh debe sobrevivir el reload o el usuario perdería la sesión en cada F5.
- **Alternativas:** (a) ambos en memoria → UX inaceptable (sesión muere en cada reload); (b) cookies httpOnly → requeriría que el backend setee/lea cookies y CSRF tokens, cambio de contrato no contemplado en C-03; el backend hoy devuelve tokens en el body. (c) refresh en `sessionStorage` → se pierde al cerrar pestaña; `localStorage` da continuidad esperable.
- **Trade-off asumido:** `localStorage` es accesible por JS → riesgo XSS. Se mitiga con la disciplina de no inyectar HTML sin sanitizar y CSP. Se documenta como riesgo (R1). Migrar a cookies httpOnly es un cambio futuro acotado al cliente + un endpoint backend.

### D2 — Refresh transparente con mutex de refresco y reencolado

El interceptor de response de Axios detecta `401` en cualquier request (excepto en `/auth/login`, `/auth/refresh`, `/auth/forgot`, `/auth/reset`, que son públicos/terminales). Al primer 401:

1. Si no hay refresh en curso, marca un flag/promesa única (`refreshPromise`) y llama `POST /api/auth/refresh`.
2. Las demás requests que reciban 401 mientras el refresh está en curso **se suscriben a la misma `refreshPromise`** (no disparan refresh propio).
3. Al resolver el refresh: se actualiza el access (memoria) y el refresh rotado (`localStorage`), y **todas** las requests originales se reintentan **una sola vez** con el nuevo token.
4. Si el refresh falla (401/invalid): se limpia la sesión y se redirige a `/login`. Las requests en cola se rechazan.

- **Por qué:** sin dedupe, N requests simultáneas con token vencido dispararían N refresh concurrentes; como el refresh **rota** (un solo uso), todos menos el primero fallarían y romperían la sesión. El mutex es obligatorio dado el contrato de rotación.
- **Anti-loop:** cada request reintentada se marca (`_retry = true`); si vuelve a dar 401 tras el reintento, no se vuelve a refrescar → se cierra sesión. Esto evita el loop infinito de refresh.
- **Alternativas:** librería externa (`axios-auth-refresh`) → se evita dependencia extra; el patrón es chico y conviene tenerlo bajo test propio y control total.

### D3 — Identidad en cliente derivada del JWT; autorización real server-side

El store de sesión decodifica el payload del JWT (base64url, sin verificar firma — el cliente no valida firmas) para extraer `sub`, `tenant_id`, `roles`, `exp`. Estos datos alimentan el menú y el guard por rol.

- **Por qué:** coherente con la regla de oro del dominio — *la identidad sale de la sesión*. En cliente "la sesión" es el JWT emitido por el backend. El cliente NO toma decisiones de seguridad reales: cada request protegida la autoriza el backend (fail-closed, 403). El guard de cliente es UX, no control de acceso.
- **Alternativas:** pedir identidad a un endpoint `/me` en cada arranque → más robusto pero hoy ese endpoint no existe; `GET /api/perfil` da datos de perfil pero no roles/permisos. Decodificar el JWT es suficiente para el menú/guard de C-21 y evita acoplar el arranque a un endpoint inexistente.

### D4 — Guard por sesión + rol, NO por permiso fino (en C-21)

`RequireAuth` exige sesión válida (access presente y no expirado, o refrescable). `RequireRole`/`RequirePermission` aceptan una lista; en C-21 se implementa la verificación contra **roles** del JWT. La interfaz del guard queda preparada para permisos finos, pero la resolución por permiso queda detrás de la Open Question OQ1.

- **Por qué:** los permisos efectivos no están en el JWT ni los expone ningún endpoint actual. Hacer guard por permiso fino requeriría inventar contrato backend, fuera del alcance de C-21.

### D5 — Stack de testing: Vitest + React Testing Library + MSW (mock de red)

Tests de componentes y de flujo con Vitest + Testing Library; el backend se mockea con **MSW** (Mock Service Worker) interceptando las llamadas Axios, no mockeando Axios en sí.

- **Por qué:** la regla del proyecto prohíbe mockear la DB, pero en frontend el "límite" testeable es la red HTTP. MSW intercepta a nivel de red → los tests ejercitan el cliente Axios + interceptores reales (incluido el refresh transparente), no un doble trivial. Esto da tests con sentido para D2.
- **Alternativas:** mockear `axios` con `vi.mock` → no ejercita los interceptores reales → test tautológico para el caso más crítico (refresh). Rechazado.

### D6 — Router: React Router v6 con rutas públicas/privadas y `lazy`

Rutas públicas (`/login`, `/2fa`, `/forgot`, `/reset`) y privadas (todo bajo el layout autenticado) con páginas `lazy`-loaded. El árbol privado se envuelve con `RequireAuth`.

- **Por qué:** la convención del proyecto pide pages lazy-loaded; React Router v6 es el estándar de facto para SPA con rutas anidadas y data/guards declarativos.

## Risks / Trade-offs

- **R1 — XSS puede exfiltrar el refresh token de `localStorage`** → Mitigación: no renderizar HTML sin sanitizar, CSP estricta, access en memoria (vida corta), y posibilidad futura de migrar a cookies httpOnly sin tocar el resto del cliente (el store de sesión es la única superficie a cambiar).
- **R2 — Loop de refresh si el reintento también da 401** → Mitigación: flag `_retry` por request; un solo reintento; al segundo 401 se cierra sesión. Cubierto por test explícito.
- **R3 — Carrera de refresh concurrente rompe la sesión por rotación de refresh** → Mitigación: mutex `refreshPromise` único (D2); test de N requests simultáneas que comparten un solo refresh.
- **R4 — Drift de contrato con el backend** (el front asume las shapes de C-03) → Mitigación: tipos TS derivados de los contratos verificados en este design; tests de servicios contra MSW con esas shapes; cualquier cambio de contrato backend rompe los tests del servicio.
- **R5 — Guard por rol da falsa sensación de seguridad** → Mitigación: documentar que el guard es UX; la autorización real es server-side (403). No se omite ninguna verificación backend por confiar en el guard.

## Migration Plan

No aplica migración de datos (frontend nuevo). Despliegue: el directorio `frontend/` se construye y sirve como artefacto estático independiente (Vite build) detrás del mismo dominio/reverse-proxy que la API. Rollback: revertir el artefacto estático; sin estado persistente del lado servidor que deshacer.

## Open Questions

- **OQ1 (PA-FE-01) — ¿Cómo obtiene el cliente los permisos efectivos para guard fino?** Hoy el JWT lleva `roles` pero no permisos, y ningún endpoint los expone. Opciones: (a) agregar `GET /api/auth/me` que devuelva `{ user, roles, permissions }` resueltos server-side (cambio backend, fuera de C-21); (b) mantener guard por rol en cliente y delegar el permiso fino al backend (decisión actual de C-21). Resolver antes de cualquier change que exija ocultar UI por permiso fino y no por rol.
- **OQ2 — ¿Persistencia del refresh: `localStorage` vs cookie httpOnly a futuro?** Decidido `localStorage` para C-21 (D1); reevaluar si se endurece la postura XSS o si el backend adopta cookies de sesión.
