import type { RankingItem } from '../types'

interface Props {
  ranking: RankingItem[]
}

export function TablaRanking({ ranking }: Props) {
  if (ranking.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin datos de ranking para esta comisión.</p>
  }

  const sorted = [...ranking].sort((a, b) => a.posicion - b.posicion)

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-600">#</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Alumno</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Legajo</th>
            <th className="px-4 py-2 text-right font-medium text-gray-600">Promedio</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {sorted.map((item) => (
            <tr key={item.alumno_id}>
              <td className="px-4 py-2 text-gray-500">{item.posicion}</td>
              <td className="px-4 py-2 font-medium text-gray-800">
                {item.apellido}, {item.nombre}
              </td>
              <td className="px-4 py-2 text-gray-500">{item.legajo}</td>
              <td className="px-4 py-2 text-right font-semibold text-indigo-700">
                {item.promedio.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
