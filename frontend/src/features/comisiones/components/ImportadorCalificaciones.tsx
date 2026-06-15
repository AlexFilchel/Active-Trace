import { useState } from 'react'
import type { Actividad, ImportacionResult } from '../types'
import { SelectorActividades } from './SelectorActividades'

interface Props {
  actividades: Actividad[]
  onImport: (file: File, actividades: string[]) => Promise<ImportacionResult>
  isLoading?: boolean
}

export function ImportadorCalificaciones({ actividades, onImport, isLoading }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [selectedActividades, setSelectedActividades] = useState<string[]>([])
  const [result, setResult] = useState<ImportacionResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || selectedActividades.length === 0) return
    setResult(null)
    setError(null)
    try {
      const res = await onImport(file, selectedActividades)
      setResult(res)
    } catch {
      setError('Error al importar calificaciones. Revisá el archivo e intentá nuevamente.')
    }
  }

  const canSubmit = !!file && selectedActividades.length > 0 && !isLoading

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="import-file" className="block text-sm font-medium text-gray-700 mb-1">
          Archivo de calificaciones (.csv)
        </label>
        <input
          id="import-file"
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm text-gray-600"
        />
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-1">Actividades a importar</p>
        <SelectorActividades
          actividades={actividades}
          selected={selectedActividades}
          onChange={setSelectedActividades}
        />
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isLoading ? 'Importando…' : 'Importar'}
      </button>

      {result && (
        <div role="status" className="rounded-md bg-green-50 p-3 text-sm text-green-800">
          Importación exitosa: {result.importados} registros. Errores: {result.errores}.
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}
    </form>
  )
}
