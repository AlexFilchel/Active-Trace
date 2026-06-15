import { Outlet, NavLink } from 'react-router-dom'
import { useSession } from '@/features/auth/hooks/useSession'
import { useNavigate } from 'react-router-dom'

interface NavEntry {
  label: string
  path: string
  roles: string[] // empty = visible to all authenticated
}

const NAV_ENTRIES: NavEntry[] = [
  { label: 'Dashboard', path: '/dashboard', roles: [] },
  { label: 'Alumnos', path: '/alumnos', roles: ['COORDINADOR', 'ADMIN', 'NEXO', 'TUTOR', 'PROFESOR'] },
  { label: 'Comisiones', path: '/comisiones', roles: ['COORDINADOR', 'ADMIN'] },
  { label: 'Liquidaciones', path: '/liquidaciones', roles: ['FINANZAS', 'ADMIN'] },
  { label: 'Administración', path: '/admin', roles: ['ADMIN'] },
]

export function AuthenticatedLayout() {
  const { roles, logout } = useSession()
  const navigate = useNavigate()

  const visibleEntries = NAV_ENTRIES.filter(
    (entry) => entry.roles.length === 0 || entry.roles.some((r) => roles.includes(r)),
  )

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Top navigation */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <nav className="flex items-center gap-4">
          <span className="font-semibold text-indigo-700 mr-4">trace</span>
          {visibleEntries.map((entry) => (
            <NavLink
              key={entry.path}
              to={entry.path}
              className={({ isActive }) =>
                `text-sm font-medium px-3 py-1 rounded-md transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              {entry.label}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={handleLogout}
          className="text-sm text-gray-600 hover:text-gray-900 px-3 py-1 rounded-md hover:bg-gray-100 transition-colors"
        >
          Cerrar sesión
        </button>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}

export default AuthenticatedLayout
