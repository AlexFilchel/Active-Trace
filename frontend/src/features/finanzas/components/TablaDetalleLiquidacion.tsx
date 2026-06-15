import type { DetalleLiquidacion, SegmentoLiquidacion } from '../types'

interface Props {
  detalles: DetalleLiquidacion[]
  segmento?: SegmentoLiquidacion
}

export function TablaDetalleLiquidacion({ detalles, segmento }: Props) {
  const filtered = segmento ? detalles.filter((d) => d.segmento === segmento) : detalles

  if (filtered.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        No hay registros para este segmento
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-2 text-left">Docente</th>
            <th className="px-4 py-2 text-left">Email</th>
            <th className="px-4 py-2 text-left">Categoría</th>
            <th className="px-4 py-2 text-right">Horas</th>
            <th className="px-4 py-2 text-right">Salario Base</th>
            <th className="px-4 py-2 text-right">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {filtered.map((d) => (
            <tr key={d.id} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-medium text-gray-800">{d.docente_nombre}</td>
              <td className="px-4 py-2 text-gray-500">{d.docente_email}</td>
              <td className="px-4 py-2">{d.categoria}</td>
              <td className="px-4 py-2 text-right">{d.horas}</td>
              <td className="px-4 py-2 text-right">${d.salario_base.toLocaleString('es-AR')}</td>
              <td className="px-4 py-2 text-right font-semibold text-indigo-700">
                ${d.total.toLocaleString('es-AR')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
