import type { Tarea, TareaEstado } from '../types'
import { TarjetaTarea } from './TarjetaTarea'

const COLUMNS: { id: TareaEstado; label: string }[] = [
  { id: 'pendiente', label: 'Pendiente' },
  { id: 'en_progreso', label: 'En progreso' },
  { id: 'completada', label: 'Completada' },
]

interface Props {
  tareas: Tarea[]
  onMover: (id: string, estado: TareaEstado) => void
}

export function KanbanTareas({ tareas, onMover }: Props) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {COLUMNS.map((col) => {
        const items = tareas.filter((t) => t.estado === col.id)
        return (
          <div key={col.id} className="flex flex-col gap-2">
            <div className="flex items-center justify-between rounded-t border-b border-gray-200 pb-2">
              <h3 className="text-sm font-medium text-gray-700">{col.label}</h3>
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                {items.length}
              </span>
            </div>
            <div className="flex flex-col gap-2 min-h-[120px]">
              {items.length === 0 ? (
                <p className="text-xs text-gray-400 italic mt-2">Sin tareas</p>
              ) : (
                items.map((t) => (
                  <TarjetaTarea key={t.id} tarea={t} onMover={onMover} />
                ))
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
