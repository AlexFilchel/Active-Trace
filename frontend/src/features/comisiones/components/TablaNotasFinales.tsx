import type { NotaFinal } from '../types'

interface Props {
  notas: NotaFinal[]
}

export function TablaNotasFinales({ notas }: Props) {
  if (notas.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin notas finales para esta comisión.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Legajo</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Alumno</th>
            <th className="px-4 py-2 text-right font-medium text-gray-600">Nota final</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Estado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {notas.map((n) => (
            <tr key={n.alumno_id}>
              <td className="px-4 py-2 text-gray-500">{n.legajo}</td>
              <td className="px-4 py-2 font-medium text-gray-800">
                {n.apellido}, {n.nombre}
              </td>
              <td className="px-4 py-2 text-right">
                {n.nota_final !== null ? n.nota_final.toFixed(2) : '—'}
              </td>
              <td className="px-4 py-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    n.estado === 'Aprobado'
                      ? 'bg-green-100 text-green-800'
                      : n.estado === 'Reprobado'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {n.estado}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
