import type { Equipo } from '../types'

interface Props {
  equipos: Equipo[]
  onDelete: (id: string) => void
  onClonar: (id: string) => void
  isDeleting?: boolean
}

export function TablaEquipos({ equipos, onDelete, onClonar, isDeleting }: Props) {
  if (equipos.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin equipos registrados.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-600">
            <th className="px-3 py-2 font-medium">Nombre</th>
            <th className="px-3 py-2 font-medium">Vigente</th>
            <th className="px-3 py-2 font-medium">Creado</th>
            <th className="px-3 py-2 font-medium">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {equipos.map((e) => (
            <tr key={e.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-3 py-2 font-medium text-gray-800">{e.nombre}</td>
              <td className="px-3 py-2">
                <span
                  className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    e.vigente ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {e.vigente ? 'Vigente' : 'Inactivo'}
                </span>
              </td>
              <td className="px-3 py-2 text-gray-500">
                {new Date(e.creado_en).toLocaleDateString('es-AR')}
              </td>
              <td className="px-3 py-2 flex gap-2">
                <button
                  onClick={() => onClonar(e.id)}
                  className="rounded bg-indigo-50 px-2 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
                >
                  Clonar
                </button>
                <button
                  onClick={() => onDelete(e.id)}
                  disabled={isDeleting}
                  className="rounded bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100 disabled:opacity-50"
                >
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
