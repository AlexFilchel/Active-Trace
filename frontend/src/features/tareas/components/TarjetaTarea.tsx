import type { Tarea, TareaEstado } from '../types'

const PRIORIDAD_BADGE: Record<string, string> = {
  baja: 'bg-gray-100 text-gray-500',
  media: 'bg-yellow-100 text-yellow-700',
  alta: 'bg-red-100 text-red-600',
}

interface Props {
  tarea: Tarea
  onMover: (id: string, estado: TareaEstado) => void
}

const NEXT_ESTADO: Record<TareaEstado, TareaEstado | null> = {
  pendiente: 'en_progreso',
  en_progreso: 'completada',
  completada: null,
}

export function TarjetaTarea({ tarea, onMover }: Props) {
  const next = NEXT_ESTADO[tarea.estado]
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <p className="text-sm font-medium text-gray-800">{tarea.titulo}</p>
      {tarea.descripcion && (
        <p className="mt-1 text-xs text-gray-500 line-clamp-2">{tarea.descripcion}</p>
      )}
      <div className="mt-2 flex items-center justify-between">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORIDAD_BADGE[tarea.prioridad] ?? PRIORIDAD_BADGE.baja}`}
        >
          {tarea.prioridad}
        </span>
        {next && (
          <button
            onClick={() => onMover(tarea.id, next)}
            className="text-xs text-indigo-600 hover:underline"
          >
            → {next.replace('_', ' ')}
          </button>
        )}
      </div>
    </div>
  )
}
