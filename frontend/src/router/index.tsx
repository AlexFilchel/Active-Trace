import { lazy, Suspense } from 'react'
import { createBrowserRouter, createMemoryRouter, Navigate } from 'react-router-dom'
import { RequireAuth } from './guards'
import AuthenticatedLayout from '@/shared/components/AuthenticatedLayout'

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'))
const TwoFactorPage = lazy(() => import('@/features/auth/pages/TwoFactorPage'))
const ForgotPasswordPage = lazy(() => import('@/features/auth/pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('@/features/auth/pages/ResetPasswordPage'))

function withSuspense(Component: React.ComponentType) {
  return (
    <Suspense fallback={<div className="p-4 text-gray-500">Cargando…</div>}>
      <Component />
    </Suspense>
  )
}

const routes = [
  // Public routes
  { path: '/login', element: withSuspense(LoginPage) },
  { path: '/2fa', element: withSuspense(TwoFactorPage) },
  { path: '/forgot', element: withSuspense(ForgotPasswordPage) },
  { path: '/reset', element: withSuspense(ResetPasswordPage) },

  // Private routes under authenticated layout
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
            <p className="mt-2 text-gray-500">Bienvenido a trace. Las secciones estarán disponibles próximamente.</p>
          </div>
        ),
      },
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
