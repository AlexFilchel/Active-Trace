import { useState } from 'react'
import type { EncuentroCreate } from '../types'

interface Props {
  onSubmit: (data: EncuentroCreate) => void
  isLoading?: boolean
}

export function FormEncuentro({ onSubmit, isLoading }: Props) {
  const [titulo, setTitulo] = useState('')
  const [fecha, setFecha] = useState('')
  const [horaInicio, setHoraInicio] = useState('')
  const [horaFin, setHoraFin] = useState('')
  const [comisionId, setComisionId] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!titulo || !fecha || !horaInicio || !horaFin || !comisionId) return
    onSubmit({
      titulo,
      fecha,
      hora_inicio: horaInicio,
      hora_fin: horaFin,
      comision_id: comisionId,
      tipo: 'clase',
    })
    setTitulo('')
    setFecha('')
    setHoraInicio('')
    setHoraFin('')
    setComisionId('')
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
      <div className="col-span-2">
        <label className="block text-xs font-medium text-gray-600 mb-1">Título</label>
        <input
          type="text"
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          placeholder="Ej: Clase 1 — Arrays"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Fecha</label>
        <input
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Comisión ID</label>
        <input
          type="text"
          value={comisionId}
          onChange={(e) => setComisionId(e.target.value)}
          placeholder="ID de la comisión"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Hora inicio</label>
        <input
          type="time"
          value={horaInicio}
          onChange={(e) => setHoraInicio(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Hora fin</label>
        <input
          type="time"
          value={horaFin}
          onChange={(e) => setHoraFin(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div className="col-span-2">
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {isLoading ? 'Guardando…' : 'Agregar encuentro'}
        </button>
      </div>
    </form>
  )
}
