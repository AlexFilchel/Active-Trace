# Tasks — C-21 frontend-shell-y-auth

> Strict TDD: por cada task de lógica, primero el test que falla, luego el código mínimo, triangular con un segundo caso, refactor. Tests sin mockear Axios directamente: usar MSW para interceptar la red. Componentes <200 LOC, sin `any`, sin class components, PascalCase. No buildear sin pedido explícito.

## 1. Scaffold y tooling

- [x] 1.1 Crear el proyecto `frontend/` con Vite (React + TypeScript) y `package.json` con scripts `dev`, `build`, `test`, `lint`
- [x] 1.2 Agregar dependencias: react-router-dom v6, @tanstack/react-query, react-hook-form, zod, @hookform/resolvers, axios
- [x] 1.3 Agregar devDependencies de testing: vitest, @testing-library/react, @testing-library/user-event, @testing-library/jest-dom, jsdom, msw
- [x] 1.4 Configurar Tailwind CSS (config + directivas en el CSS de entrada) y verificar que una clase utilitaria aplica
- [x] 1.5 Configurar TypeScript estricto (`strict: true`, `noImplicitAny`) y alias `@/` a `src/`
- [x] 1.6 Configurar Vitest (entorno jsdom, setup file con jest-dom y arranque/cierre del server de MSW)
- [x] 1.7 Crear la estructura de carpetas: `src/features/auth/{components,hooks,services,types,pages}` y `src/shared/{services,components,hooks}`

## 2. Cliente HTTP centralizado (frontend-http-client)

- [x] 2.1 Definir los tipos del store de sesión y los contratos de auth en `features/auth/types` (LoginResponse con variante tokens y variante `requires_two_factor`, RefreshResponse)
- [x] 2.2 RED→GREEN: store de sesión en `shared/services` (o `features/auth/services`) — access en memoria, refresh en localStorage; getters de access/refresh, setters, clear. Test: set/get/clear y persistencia del refresh tras "reload" (re-import del módulo / mock de localStorage)
- [x] 2.3 RED→GREEN: decodificador de claims del JWT (`sub`, `tenant_id`, `roles`, `exp`) en el store. Test: token válido devuelve claims; token con `exp` pasado se considera expirado (triangular con `exp` futuro)
- [x] 2.4 Crear la instancia Axios única en `shared/services/api` con baseURL y JSON defaults. Test (MSW): una request de un service usa esta instancia y pega al endpoint esperado
- [x] 2.5 RED→GREEN: interceptor de request que inyecta `Authorization: Bearer <access>` cuando hay sesión. Test (MSW): con sesión, el header llega; sin sesión en endpoint público, no llega (triangular)
- [x] 2.6 RED→GREEN: interceptor de response — refresh transparente en 401, reintento único de la request original con el nuevo access. Test (MSW): primer 401 → llama `/auth/refresh` → reintenta y resuelve 200
- [x] 2.7 TRIANGULAR: dedupe de refresh concurrente (mutex `refreshPromise`). Test (MSW): N requests simultáneas con 401 disparan exactamente UN `/auth/refresh` y todas se reintentan con el nuevo token
- [x] 2.8 TRIANGULAR: anti-loop — request ya reintentada que vuelve a dar 401 NO refresca de nuevo; refresh que falla limpia sesión y redirige a `/login`. Test (MSW): ambos casos
- [x] 2.9 RED→GREEN: 403 propaga error de autorización sin refrescar ni reintentar. Test (MSW): un 403 no genera llamada a `/auth/refresh`

## 3. Servicios de auth (frontend-auth-session — capa de red)

- [x] 3.1 RED→GREEN: `authService.login(email, password, tenantSlug?)` → `POST /api/auth/login`. Test (MSW): respuesta con tokens vs respuesta `requires_two_factor` (triangular)
- [x] 3.2 RED→GREEN: `authService.verifyLogin2fa(challengeToken, code)` → `POST /api/auth/2fa/verify-login`. Test (MSW): código válido devuelve tokens; inválido propaga error (triangular)
- [x] 3.3 RED→GREEN: `authService.forgotPassword(email)` → `POST /api/auth/forgot`. Test (MSW): siempre resuelve con confirmación neutra
- [x] 3.4 RED→GREEN: `authService.resetPassword(token, newPassword)` → `POST /api/auth/reset`. Test (MSW): token válido OK; token inválido propaga error (triangular)
- [x] 3.5 RED→GREEN: `authService.logout(refreshToken)` → `POST /api/auth/logout`. Test (MSW): éxito 204; ante fallo el caller igual debe poder limpiar sesión

## 4. Hooks de sesión (TanStack Query / RHF)

- [x] 4.1 RED→GREEN: hook `useLogin` (mutation) que en éxito con tokens establece la sesión y en `requires_two_factor` expone el `challenge_token`. Test: ambos caminos (triangular)
- [x] 4.2 RED→GREEN: hook `useSession` que expone `isAuthenticated`, identidad (user id, tenant, roles) y `logout`. Test: con/ sin sesión; roles derivados del JWT
- [x] 4.3 RED→GREEN: rehidratación al arranque — al montar, si hay refresh persistido se refresca el access y se restablece la sesión. Test (MSW): refresh válido restaura sesión; sin refresh válido → sin sesión (triangular)

## 5. Pantallas de autenticación (frontend-auth-session — UI)

- [x] 5.1 RED→GREEN: `LoginPage` con form (email, password, tenant opcional) validado con RHF+Zod. Test: render de campos y submit (loading/error states presentes)
- [x] 5.2 TRIANGULAR `LoginPage`: login feliz (mock) establece sesión y navega al área autenticada; credenciales inválidas muestran error sin sesión; respuesta 2FA enruta al challenge con el `challenge_token`
- [x] 5.3 RED→GREEN: `TwoFactorPage` con input de código TOTP → verify-login. Test: código válido establece sesión; inválido muestra error (triangular)
- [x] 5.4 RED→GREEN: `ForgotPasswordPage`. Test: submit muestra confirmación neutra independientemente del email
- [x] 5.5 RED→GREEN: `ResetPasswordPage` (lee token de la URL). Test: token válido permite resetear y seguir a login; token inválido muestra error (triangular)

## 6. Router, guard y layout (frontend-app-shell)

- [x] 6.1 RED→GREEN: componente `RequireAuth` — sin sesión redirige a `/login`; con sesión renderiza el contenido. Test: ambos casos (triangular)
- [x] 6.2 TRIANGULAR: `RequireRole`/guard por rol — sesión sin el rol requerido renderiza estado "sin acceso"; con el rol requerido renderiza la ruta. Test: ambos casos
- [x] 6.3 RED→GREEN: configurar el router con rutas públicas (`/login`, `/2fa`, `/forgot`, `/reset`) y privadas bajo el layout autenticado, con pages `lazy`. Test: ruta privada sin sesión redirige a `/login`; ruta pública renderiza sin redirigir
- [x] 6.4 RED→GREEN: `AuthenticatedLayout` con menú cuyas entradas se muestran/ocultan según los roles de la sesión y una acción de logout visible. Test: el menú refleja los roles; el control de logout dispara el flujo de logout
- [x] 6.5 RED→GREEN: `App` raíz con `QueryClientProvider`, router y provider de sesión. Test: la app monta y renderiza sin errores

## 7. Cierre

- [ ] 7.1 Verificar cobertura del flujo crítico: render de login, login feliz (mock), guard sin sesión redirige, refresh transparente reintenta y no entra en loop, dedupe de refresh concurrente
- [ ] 7.2 Lint y typecheck sin errores (`tsc --noEmit`, lint) — sin `any`, sin class components, componentes <200 LOC
- [ ] 7.3 Documentar en el README de `frontend/` cómo correr dev y tests, y dejar registradas las open questions OQ1 (endpoint de permisos para guard fino) y OQ2 (persistencia del refresh)
