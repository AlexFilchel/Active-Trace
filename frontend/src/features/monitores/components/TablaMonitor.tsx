import type { MonitorItem } from '../types'

interface Props {
  items: MonitorItem[]
}

export function TablaMonitor({ items }: Props) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin alumnos en el monitor.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-600">
            <th className="px-3 py-2 font-medium">Alumno</th>
            <th className="px-3 py-2 font-medium">Legajo</th>
            <th className="px-3 py-2 font-medium">Comisión</th>
            <th className="px-3 py-2 font-medium">Estado</th>
            <th className="px-3 py-2 font-medium">Pendientes</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.alumno_id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-3 py-2 text-gray-800">
                {item.apellido}, {item.nombre}
              </td>
              <td className="px-3 py-2 text-gray-500">{item.legajo}</td>
              <td className="px-3 py-2 text-gray-500">{item.comision_id}</td>
              <td className="px-3 py-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    item.estado === 'atrasado'
                      ? 'bg-red-100 text-red-600'
                      : 'bg-green-100 text-green-700'
                  }`}
                >
                  {item.estado}
                </span>
              </td>
              <td className="px-3 py-2 text-center text-gray-700">
                {item.actividades_pendientes}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
