import type { ReporteRapido as ReporteRapidoType } from '../types'

interface Props {
  reporte?: ReporteRapidoType
}

export function ReporteRapido({ reporte }: Props) {
  if (!reporte || reporte.total_alumnos === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        Sin datos disponibles para el reporte rápido.
      </p>
    )
  }

  const metrics = [
    { label: 'Total alumnos', value: reporte.total_alumnos },
    { label: 'Aprobados', value: reporte.aprobados },
    { label: 'Reprobados', value: reporte.reprobados },
    { label: 'Sin nota', value: reporte.sin_nota },
    { label: 'Atrasados', value: reporte.atrasados },
  ]

  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg bg-white border border-gray-200 p-3 text-center">
            <dt className="text-xs text-gray-500">{m.label}</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">{m.value}</dd>
          </div>
        ))}
      </dl>
      {reporte.promedio_general !== null && (
        <p className="text-sm text-gray-600">
          Promedio general:{' '}
          <span className="font-semibold text-indigo-700">
            {reporte.promedio_general.toFixed(2)}
          </span>
        </p>
      )}
    </div>
  )
}
