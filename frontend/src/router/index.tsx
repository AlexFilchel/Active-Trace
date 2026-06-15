import { lazy, Suspense, useMemo } from 'react'
import { createBrowserRouter, createMemoryRouter, Navigate } from 'react-router-dom'
import { RequireAuth } from './guards'
import AuthenticatedLayout from '@/shared/components/AuthenticatedLayout'

// ── Auth ─────────────────────────────────────────────────────────────────────
const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'))
const TwoFactorPage = lazy(() => import('@/features/auth/pages/TwoFactorPage'))
const ForgotPasswordPage = lazy(() => import('@/features/auth/pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('@/features/auth/pages/ResetPasswordPage'))

// ── C-22: Académico / Docente ─────────────────────────────────────────────────
const ComisionesPage = lazy(() =>
  import('@/features/comisiones/pages/ComisionesPage').then((m) => ({ default: m.ComisionesPage })),
)

// ── C-23: Coordinación ───────────────────────────────────────────────────────
const EquiposPage = lazy(() =>
  import('@/features/equipos/pages/EquiposPage').then((m) => ({ default: m.EquiposPage })),
)
const AvisosPage = lazy(() =>
  import('@/features/avisos/pages/AvisosPage').then((m) => ({ default: m.AvisosPage })),
)
const TareasPage = lazy(() =>
  import('@/features/tareas/pages/TareasPage').then((m) => ({ default: m.TareasPage })),
)
const MonitoresPage = lazy(() =>
  import('@/features/monitores/pages/MonitoresPage').then((m) => ({ default: m.MonitoresPage })),
)

// ── C-24: Finanzas / Admin ────────────────────────────────────────────────────
const LiquidacionesPage = lazy(() =>
  import('@/features/finanzas/pages/LiquidacionesPage').then((m) => ({ default: m.LiquidacionesPage })),
)

function withSuspense(Component: React.ComponentType) {
  return (
    <Suspense fallback={<div className="p-4 text-gray-500">Cargando…</div>}>
      <Component />
    </Suspense>
  )
}

const routes = [
  // ── Públicas ──────────────────────────────────────────────────────────────
  { path: '/login', element: withSuspense(LoginPage) },
  { path: '/2fa', element: withSuspense(TwoFactorPage) },
  { path: '/forgot', element: withSuspense(ForgotPasswordPage) },
  { path: '/reset', element: withSuspense(ResetPasswordPage) },

  // ── Privadas ──────────────────────────────────────────────────────────────
  {
    path: '/',
    element: (
      <RequireAuth>
        <AuthenticatedLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: (
          <div className="p-8">
            <h1 className="text-2xl font-semibold text-gray-800">Dashboard</h1>
            <p className="mt-2 text-gray-500">Bienvenido a trace.</p>
          </div>
        ),
      },
      // C-22
      { path: 'comisiones', element: withSuspense(ComisionesPage) },
      // C-23
      { path: 'equipos', element: withSuspense(EquiposPage) },
      { path: 'avisos', element: withSuspense(AvisosPage) },
      { path: 'tareas', element: withSuspense(TareasPage) },
      { path: 'monitores', element: withSuspense(MonitoresPage) },
      // C-24
      { path: 'liquidaciones', element: withSuspense(LiquidacionesPage) },
      // Placeholder para secciones sin implementar aún
      {
        path: '*',
        element: (
          <div className="p-8">
            <h2 className="text-xl font-semibold text-gray-700">Próximamente</h2>
            <p className="mt-2 text-gray-500">Esta sección está en desarrollo.</p>
          </div>
        ),
      },
    ],
  },
]

interface CreateAppRouterOptions {
  initialPath?: string
}

export function createAppRouter({ initialPath }: CreateAppRouterOptions = {}) {
  if (initialPath !== undefined) {
    return createMemoryRouter(routes, { initialEntries: [initialPath] })
  }
  return createBrowserRouter(routes)
}
