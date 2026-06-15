import { useState } from 'react'
import type { GrillaSalarial as GrillaSalarialType } from '../types'
import { FormularioGrilla } from './FormularioGrilla'

interface Props {
  grillas: GrillaSalarialType[]
  onCrear: (data: { categoria: string; salario_base: number }) => void
  onEditar: (id: string, data: { categoria: string; salario_base: number }) => void
  onEliminar: (id: string) => void
  isLoading?: boolean
}

export function GrillaSalarial({ grillas, onCrear, onEditar, onEliminar, isLoading }: Props) {
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<GrillaSalarialType | null>(null)

  const handleSubmit = (data: { categoria: string; salario_base: number }) => {
    if (editing) {
      onEditar(editing.id, data)
    } else {
      onCrear(data)
    }
    setShowForm(false)
    setEditing(null)
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-gray-700">Grilla Salarial</h3>
        <button
          onClick={() => { setShowForm(true); setEditing(null) }}
          className="text-sm px-3 py-1 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          + Nueva categoría
        </button>
      </div>

      {(showForm || editing) && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <FormularioGrilla
            initial={editing ?? undefined}
            onSubmit={handleSubmit}
            onCancel={() => { setShowForm(false); setEditing(null) }}
            isLoading={isLoading}
          />
        </div>
      )}

      {grillas.length === 0 ? (
        <div className="text-center text-gray-400 py-8">No hay categorías definidas</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-2 text-left">Categoría</th>
              <th className="px-4 py-2 text-right">Salario Base</th>
              <th className="px-4 py-2 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {grillas.map((g) => (
              <tr key={g.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-800">{g.categoria}</td>
                <td className="px-4 py-2 text-right">${g.salario_base.toLocaleString('es-AR')}</td>
                <td className="px-4 py-2 text-right space-x-2">
                  <button
                    onClick={() => { setEditing(g); setShowForm(false) }}
                    className="text-indigo-600 hover:underline text-xs"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => onEliminar(g.id)}
                    className="text-red-500 hover:underline text-xs"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
