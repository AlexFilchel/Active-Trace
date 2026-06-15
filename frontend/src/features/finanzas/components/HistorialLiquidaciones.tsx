import type { Liquidacion } from '../types'

interface Props {
  historial: Liquidacion[]
}

export function HistorialLiquidaciones({ historial }: Props) {
  if (historial.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        No hay liquidaciones anteriores
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-2 text-left">Período</th>
            <th className="px-4 py-2 text-left">Estado</th>
            <th className="px-4 py-2 text-right">Docentes</th>
            <th className="px-4 py-2 text-right">Total Honorarios</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {historial.map((liq) => (
            <tr key={liq.id} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-medium text-gray-800">{liq.periodo}</td>
              <td className="px-4 py-2">
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    liq.estado === 'CERRADA'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}
                >
                  {liq.estado}
                </span>
              </td>
              <td className="px-4 py-2 text-right">{liq.total_docentes}</td>
              <td className="px-4 py-2 text-right font-semibold">
                ${liq.total_honorarios.toLocaleString('es-AR')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
