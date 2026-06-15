import type { EstadoDestinatario, EstadoComunicacion } from '../types'

interface Props {
  estados: EstadoDestinatario[]
}

const ESTADO_STYLES: Record<EstadoComunicacion, string> = {
  Pendiente: 'bg-yellow-100 text-yellow-800',
  Enviando: 'bg-blue-100 text-blue-800',
  OK: 'bg-green-100 text-green-800',
  Fallido: 'bg-red-100 text-red-800',
  Cancelado: 'bg-gray-100 text-gray-600',
}

export function PanelEstadoComunicaciones({ estados }: Props) {
  if (estados.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        Sin comunicaciones enviadas para esta comisión.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Legajo</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Destinatario</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Estado</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">Detalle</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {estados.map((e) => (
            <tr key={e.alumno_id}>
              <td className="px-4 py-2 text-gray-500">{e.legajo}</td>
              <td className="px-4 py-2 font-medium text-gray-800">
                {e.apellido}, {e.nombre}
              </td>
              <td className="px-4 py-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_STYLES[e.estado] ?? 'bg-gray-100 text-gray-600'}`}
                >
                  {e.estado}
                </span>
              </td>
              <td className="px-4 py-2 text-gray-500 text-xs">{e.error ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
