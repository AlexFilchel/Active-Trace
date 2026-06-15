import { useState } from 'react'
import type { Factura, EstadoFactura } from '../types'
import { FormularioFactura } from './FormularioFactura'

interface Props {
  facturas: Factura[]
  onCrear: (data: { proveedor: string; monto: number; descripcion: string }) => void
  onCambiarEstado: (id: string, estado: EstadoFactura) => void
  isLoading?: boolean
}

const estadoBadge: Record<EstadoFactura, string> = {
  PENDIENTE: 'bg-yellow-100 text-yellow-700',
  APROBADA: 'bg-green-100 text-green-700',
  RECHAZADA: 'bg-red-100 text-red-700',
}

export function TablaFacturas({ facturas, onCrear, onCambiarEstado, isLoading }: Props) {
  const [showForm, setShowForm] = useState(false)

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-gray-700">Facturas</h3>
        <button
          onClick={() => setShowForm(true)}
          className="text-sm px-3 py-1 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          + Nueva factura
        </button>
      </div>

      {showForm && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <FormularioFactura
            onSubmit={(data) => { onCrear(data); setShowForm(false) }}
            onCancel={() => setShowForm(false)}
            isLoading={isLoading}
          />
        </div>
      )}

      {facturas.length === 0 ? (
        <div className="text-center text-gray-400 py-8">No hay facturas registradas</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-2 text-left">Proveedor</th>
              <th className="px-4 py-2 text-right">Monto</th>
              <th className="px-4 py-2 text-left">Descripción</th>
              <th className="px-4 py-2 text-left">Fecha</th>
              <th className="px-4 py-2 text-left">Estado</th>
              <th className="px-4 py-2 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {facturas.map((f) => (
              <tr key={f.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-800">{f.proveedor}</td>
                <td className="px-4 py-2 text-right">${f.monto.toLocaleString('es-AR')}</td>
                <td className="px-4 py-2 text-gray-600">{f.descripcion}</td>
                <td className="px-4 py-2 text-gray-500">{f.fecha}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${estadoBadge[f.estado]}`}>
                    {f.estado}
                  </span>
                </td>
                <td className="px-4 py-2 text-right space-x-2">
                  {f.estado === 'PENDIENTE' && (
                    <>
                      <button
                        onClick={() => onCambiarEstado(f.id, 'APROBADA')}
                        className="text-green-600 hover:underline text-xs"
                      >
                        Aprobar
                      </button>
                      <button
                        onClick={() => onCambiarEstado(f.id, 'RECHAZADA')}
                        className="text-red-500 hover:underline text-xs"
                      >
                        Rechazar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
