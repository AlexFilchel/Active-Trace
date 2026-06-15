import type { Actividad } from '../types'

interface Props {
  actividades: Actividad[]
  selected: string[]
  onChange: (ids: string[]) => void
}

export function SelectorActividades({ actividades, selected, onChange }: Props) {
  if (actividades.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        No hay actividades disponibles para esta comisión.
      </p>
    )
  }

  function toggle(id: string) {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id))
    } else {
      onChange([...selected, id])
    }
  }

  return (
    <ul className="space-y-1">
      {actividades.map((act) => (
        <li key={act.id} className="flex items-center gap-2">
          <input
            type="checkbox"
            id={`act-${act.id}`}
            checked={selected.includes(act.id)}
            onChange={() => toggle(act.id)}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <label htmlFor={`act-${act.id}`} className="text-sm text-gray-700">
            {act.nombre}
            {act.tipo && (
              <span className="ml-2 text-xs text-gray-400">({act.tipo})</span>
            )}
          </label>
        </li>
      ))}
    </ul>
  )
}
