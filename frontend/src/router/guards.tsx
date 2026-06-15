import { Navigate } from 'react-router-dom'
import { useSession } from '@/features/auth/hooks/useSession'

interface RequireAuthProps {
  children: React.ReactNode
}

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated } = useSession()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

interface RequireRoleProps {
  children: React.ReactNode
  roles: string[]
}

export function RequireRole({ children, roles }: RequireRoleProps) {
  const { isAuthenticated, roles: sessionRoles } = useSession()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const hasRole = roles.some((r) => sessionRoles.includes(r))

  if (!hasRole) {
    return (
      <div className="flex items-center justify-center min-h-64 p-8">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Acceso denegado</h2>
          <p className="text-gray-600">Sin acceso a esta sección.</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
