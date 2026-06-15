import type { EntregaSinCorregir } from '../types'

interface Props {
  entregas: EntregaSinCorregir[]
  onExport?: () => void
}

export function TablaEntregasSinCorregir({ entregas, onExport }: Props) {
  if (entregas.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-500 italic">
          Sin entregas pendientes de corrección.
        </p>
        <button
          disabled
          className="rounded-md bg-gray-200 px-3 py-1.5 text-sm font-medium text-gray-400 cursor-not-allowed"
        >
          Exportar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Legajo</th>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Alumno</th>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Actividad</th>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Fecha entrega</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {entregas.map((e) => (
              <tr key={`${e.alumno_id}-${e.actividad_id}`}>
                <td className="px-4 py-2 text-gray-500">{e.legajo}</td>
                <td className="px-4 py-2 font-medium text-gray-800">
                  {e.apellido}, {e.nombre}
                </td>
                <td className="px-4 py-2 text-gray-600">{e.actividad_nombre}</td>
                <td className="px-4 py-2 text-gray-500">{e.fecha_entrega}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        onClick={onExport}
        className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
      >
        Exportar
      </button>
    </div>
  )
}
