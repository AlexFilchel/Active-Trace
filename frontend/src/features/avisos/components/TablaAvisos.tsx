import type { Aviso } from '../types'

interface Props {
  avisos: Aviso[]
  onDelete: (id: string) => void
  isDeleting?: boolean
}

export function TablaAvisos({ avisos, onDelete, isDeleting }: Props) {
  if (avisos.length === 0) {
    return <p className="text-sm text-gray-500 italic">Sin avisos publicados.</p>
  }
  return (
    <div className="space-y-2">
      {avisos.map((a) => (
        <div key={a.id} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-medium text-gray-800">{a.titulo}</p>
              <p className="mt-1 text-sm text-gray-600">{a.cuerpo}</p>
              <div className="mt-2 flex gap-2 text-xs text-gray-400">
                <span className="rounded bg-gray-100 px-2 py-0.5">{a.scope}</span>
                <span>{new Date(a.creado_en).toLocaleDateString('es-AR')}</span>
              </div>
            </div>
            <button
              onClick={() => onDelete(a.id)}
              disabled={isDeleting}
              className="shrink-0 rounded bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100 disabled:opacity-50"
            >
              Eliminar
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
