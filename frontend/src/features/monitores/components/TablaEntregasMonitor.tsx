import type { EntregaMonitor } from '../types'

interface Props {
  entregas: EntregaMonitor[]
}

export function TablaEntregasMonitor({ entregas }: Props) {
  if (entregas.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin entregas pendientes de corrección.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-600">
            <th className="px-3 py-2 font-medium">Alumno</th>
            <th className="px-3 py-2 font-medium">Actividad</th>
            <th className="px-3 py-2 font-medium">Comisión</th>
            <th className="px-3 py-2 font-medium">Fecha entrega</th>
          </tr>
        </thead>
        <tbody>
          {entregas.map((e) => (
            <tr
              key={`${e.alumno_id}-${e.actividad_id}`}
              className="border-b border-gray-100 hover:bg-gray-50"
            >
              <td className="px-3 py-2 text-gray-800">
                {e.apellido}, {e.nombre}
              </td>
              <td className="px-3 py-2 text-gray-700">{e.actividad_nombre}</td>
              <td className="px-3 py-2 text-gray-500">{e.comision_id}</td>
              <td className="px-3 py-2 text-gray-500">
                {new Date(e.fecha_entrega).toLocaleDateString('es-AR')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
