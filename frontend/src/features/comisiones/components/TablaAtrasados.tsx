import type { AlumnoAtrasado } from '../types'

interface Props {
  atrasados: AlumnoAtrasado[]
}

export function TablaAtrasados({ atrasados }: Props) {
  if (atrasados.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        Sin alumnos atrasados en esta comisión.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Legajo</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Alumno</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Motivo</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Actividades pendientes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {atrasados.map((a) => (
            <tr key={a.alumno_id}>
              <td className="px-4 py-2 text-gray-500">{a.legajo}</td>
              <td className="px-4 py-2 font-medium text-gray-800">
                {a.apellido}, {a.nombre}
              </td>
              <td className="px-4 py-2 text-gray-600">{a.motivo}</td>
              <td className="px-4 py-2 text-gray-500">{a.actividades_pendientes.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
