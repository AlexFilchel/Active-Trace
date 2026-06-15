import type { Encuentro } from '../types'

interface Props {
  encuentros: Encuentro[]
  onDelete: (id: string) => void
}

export function TablaEncuentros({ encuentros, onDelete }: Props) {
  if (encuentros.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin encuentros programados.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-600">
            <th className="px-3 py-2 font-medium">Título</th>
            <th className="px-3 py-2 font-medium">Fecha</th>
            <th className="px-3 py-2 font-medium">Horario</th>
            <th className="px-3 py-2 font-medium">Tipo</th>
            <th className="px-3 py-2 font-medium">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {encuentros.map((e) => (
            <tr key={e.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-3 py-2 font-medium text-gray-800">{e.titulo}</td>
              <td className="px-3 py-2 text-gray-600">
                {new Date(e.fecha).toLocaleDateString('es-AR')}
              </td>
              <td className="px-3 py-2 text-gray-600">
                {e.hora_inicio} – {e.hora_fin}
              </td>
              <td className="px-3 py-2">
                <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
                  {e.tipo}
                </span>
              </td>
              <td className="px-3 py-2">
                <button
                  onClick={() => onDelete(e.id)}
                  className="rounded bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100"
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
