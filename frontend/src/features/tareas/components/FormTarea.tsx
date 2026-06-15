import { useState } from 'react'
import type { TareaCreate } from '../types'

interface Props {
  onSubmit: (data: TareaCreate) => void
  isLoading?: boolean
}

export function FormTarea({ onSubmit, isLoading }: Props) {
  const [titulo, setTitulo] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!titulo.trim()) return
    onSubmit({ titulo, prioridad: 'media' })
    setTitulo('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <div className="flex-1">
        <label htmlFor="tarea-titulo" className="block text-xs font-medium text-gray-600 mb-1">
          Nueva tarea
        </label>
        <input
          id="tarea-titulo"
          type="text"
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          placeholder="Descripción de la tarea…"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !titulo.trim()}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isLoading ? 'Creando…' : 'Crear'}
      </button>
    </form>
  )
}
