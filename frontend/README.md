# activia-trace — Frontend

SPA de activia-trace construida con React 18 + TypeScript + Vite.

## Comandos

```bash
# Desarrollo
npm run dev        # Levanta el servidor de desarrollo (http://localhost:5173)

# Tests
npm run test       # Corre todos los tests (Vitest, modo run)
npm run test:watch # Modo watch para TDD

# Calidad
npm run lint       # ESLint
npx tsc --noEmit   # Typecheck sin compilar
```

## Estructura

```
src/
├── features/
│   └── auth/
│       ├── components/   # Componentes reutilizables del feature
│       ├── hooks/        # useLogin, useSession, useRehydrateSession
│       ├── pages/        # LoginPage, TwoFactorPage, ForgotPasswordPage, ResetPasswordPage
│       ├── services/     # authService, sessionStore
│       └── types/        # Contratos de auth (LoginResponse, JwtClaims, etc.)
├── shared/
│   ├── components/       # AuthenticatedLayout
│   ├── hooks/            # Hooks transversales
│   └── services/         # api.ts — instancia Axios centralizada
├── router/
│   ├── index.tsx         # createAppRouter()
│   └── guards.tsx        # RequireAuth, RequireRole
└── test/
    ├── server.ts         # Servidor MSW (nodo)
    └── setup.ts          # Setup de Vitest + jest-dom + MSW
```

## Decisiones de diseño relevantes

- **Access token en memoria** — no persiste entre recargas. Reduce superficie XSS.
- **Refresh token en `localStorage`** — sobrevive recargas; la app lo usa para rehidratar la sesión al arrancar.
- **Refresh transparente con mutex** — si múltiples requests reciben 401 simultáneamente, se dispara UN SOLO refresh; todas las demás requests aguardan y se reintentan con el nuevo token.
- **Identity del JWT** — el cliente decodifica el payload (sin verificar firma) para leer `sub`, `tenant_id`, `roles`, `exp`. La autorización real es siempre server-side.
- **Tests con MSW** — nunca se mockea Axios directamente. MSW intercepta a nivel de red para que los interceptores reales (incluyendo el refresh) sean ejercitados.

## Open Questions

- **OQ1 (PA-FE-01)** — Guard por permiso fino: hoy el guard usa `roles` del JWT. Los permisos efectivos no están en el JWT ni hay endpoint que los exponga. Opciones: agregar `GET /api/auth/me` que devuelva `{ roles, permissions }` (cambio backend), o mantener guard por rol en cliente y delegar permiso fino al backend (actual). Resolver antes de cualquier change que requiera ocultar UI por permiso fine-grained.
- **OQ2** — Migración de refresh a `httpOnly cookie`: la decisión actual usa `localStorage` (accesible por JS). Si se endurece la postura XSS, migrar a cookie httpOnly requiere un endpoint backend que lea/sette la cookie y manejo de CSRF. Cambio acotado al `sessionStore.ts` y un endpoint backend.
