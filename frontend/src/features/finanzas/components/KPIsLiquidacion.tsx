import type { Liquidacion } from '../types'

interface Props {
  liquidacion: Liquidacion | undefined
  isLoading?: boolean
}

export function KPIsLiquidacion({ liquidacion, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse h-20" />
        ))}
      </div>
    )
  }

  if (!liquidacion) {
    return (
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center text-gray-400 col-span-3">
          Sin datos de liquidación para el período seleccionado
        </div>
      </div>
    )
  }

  const estadoColor =
    liquidacion.estado === 'ABIERTA'
      ? 'text-yellow-600 bg-yellow-50 border-yellow-200'
      : 'text-green-600 bg-green-50 border-green-200'

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Docentes</p>
        <p className="text-2xl font-bold text-gray-800 mt-1">{liquidacion.total_docentes}</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Total Honorarios</p>
        <p className="text-2xl font-bold text-indigo-700 mt-1">
          ${liquidacion.total_honorarios.toLocaleString('es-AR')}
        </p>
      </div>
      <div className={`rounded-lg border p-4 ${estadoColor}`}>
        <p className="text-xs uppercase tracking-wide font-medium">Estado</p>
        <p className="text-xl font-bold mt-1">{liquidacion.estado}</p>
      </div>
    </div>
  )
}
