import { useState } from 'react'
import type { AvisoCreate, AvisoScope } from '../types'

interface Props {
  onSubmit: (data: AvisoCreate) => void
  isLoading?: boolean
}

export function FormAviso({ onSubmit, isLoading }: Props) {
  const [titulo, setTitulo] = useState('')
  const [cuerpo, setCuerpo] = useState('')
  const [scope, setScope] = useState<AvisoScope>('tenant')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!titulo.trim() || !cuerpo.trim()) return
    onSubmit({ titulo, cuerpo, scope })
    setTitulo('')
    setCuerpo('')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label htmlFor="aviso-titulo" className="block text-xs font-medium text-gray-600 mb-1">
          Título
        </label>
        <input
          id="aviso-titulo"
          type="text"
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          placeholder="Título del aviso"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <label htmlFor="aviso-cuerpo" className="block text-xs font-medium text-gray-600 mb-1">
          Contenido
        </label>
        <textarea
          id="aviso-cuerpo"
          value={cuerpo}
          onChange={(e) => setCuerpo(e.target.value)}
          rows={3}
          placeholder="Texto del aviso…"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <label htmlFor="aviso-scope" className="block text-xs font-medium text-gray-600 mb-1">
          Alcance
        </label>
        <select
          id="aviso-scope"
          value={scope}
          onChange={(e) => setScope(e.target.value as AvisoScope)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="tenant">Toda la institución</option>
          <option value="cohorte">Cohorte</option>
          <option value="comision">Comisión</option>
        </select>
      </div>
      <button
        type="submit"
        disabled={isLoading || !titulo.trim() || !cuerpo.trim()}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isLoading ? 'Publicando…' : 'Publicar aviso'}
      </button>
    </form>
  )
}
