import { useState } from 'react'
import type { EquipoCreate } from '../types'

interface Props {
  onSubmit: (data: EquipoCreate) => void
  isLoading?: boolean
}

export function FormEquipo({ onSubmit, isLoading }: Props) {
  const [nombre, setNombre] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!nombre.trim()) return
    onSubmit({ nombre })
    setNombre('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <div className="flex-1">
        <label htmlFor="equipo-nombre" className="block text-xs font-medium text-gray-600 mb-1">
          Nombre del equipo
        </label>
        <input
          id="equipo-nombre"
          type="text"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej: Tutores 2024-1"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !nombre.trim()}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isLoading ? 'Creando…' : 'Crear equipo'}
      </button>
    </form>
  )
}
