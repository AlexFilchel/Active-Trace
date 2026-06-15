import { useState } from 'react'
import type { AlumnoAtrasado } from '../types'

interface Props {
  atrasados: AlumnoAtrasado[]
}

export function MonitorSeguimiento({ atrasados }: Props) {
  const [filtroNombre, setFiltroNombre] = useState('')
  const [minimoActividades, setMinimoActividades] = useState(1)

  const filtered = atrasados.filter((a) => {
    const fullName = `${a.apellido} ${a.nombre}`.toLowerCase()
    const matchNombre = filtroNombre === '' || fullName.includes(filtroNombre.toLowerCase())
    const matchMinimo = a.actividades_pendientes.length >= minimoActividades
    return matchNombre && matchMinimo
  })

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <div>
          <label htmlFor="filtro-nombre" className="block text-xs font-medium text-gray-600 mb-1">
            Filtrar por alumno
          </label>
          <input
            id="filtro-nombre"
            type="text"
            value={filtroNombre}
            onChange={(e) => setFiltroNombre(e.target.value)}
            placeholder="Buscar por nombre…"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="minimo-actividades" className="block text-xs font-medium text-gray-600 mb-1">
            Mínimo actividades pendientes
          </label>
          <input
            id="minimo-actividades"
            type="number"
            min={1}
            value={minimoActividades}
            onChange={(e) => setMinimoActividades(Number(e.target.value))}
            className="w-20 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-gray-500 italic">Sin alumnos que coincidan con los filtros.</p>
      ) : (
        <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {filtered.map((a) => (
            <li key={a.alumno_id} className="flex items-start justify-between px-4 py-2">
              <div>
                <p className="text-sm font-medium text-gray-800">
                  {a.apellido}, {a.nombre}
                </p>
                <p className="text-xs text-gray-500">Legajo: {a.legajo}</p>
                <p className="text-xs text-gray-500 mt-0.5">{a.motivo}</p>
              </div>
              <span className="text-xs font-semibold text-red-600 bg-red-50 rounded-full px-2 py-0.5">
                {a.actividades_pendientes.length} pendiente(s)
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
