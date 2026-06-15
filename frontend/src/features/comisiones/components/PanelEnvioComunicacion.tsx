import { useState } from 'react'
import type { ComunicacionPreview } from '../types'

interface Props {
  preview?: ComunicacionPreview
  onConfirm: (mensajePersonalizado?: string) => void
  isSending?: boolean
}

export function PanelEnvioComunicacion({ preview, onConfirm, isSending }: Props) {
  const [mensajePersonalizado, setMensajePersonalizado] = useState('')

  const canSend = !!preview && !isSending

  function handleSend() {
    if (!canSend) return
    onConfirm(mensajePersonalizado || undefined)
  }

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="mensaje-personalizado" className="block text-sm font-medium text-gray-700 mb-1">
          Mensaje personalizado (opcional)
        </label>
        <textarea
          id="mensaje-personalizado"
          value={mensajePersonalizado}
          onChange={(e) => setMensajePersonalizado(e.target.value)}
          rows={3}
          placeholder="Agregar texto adicional al mensaje…"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>
      <button
        onClick={handleSend}
        disabled={!canSend}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        title={!preview ? 'Generá una preview primero' : undefined}
      >
        {isSending ? 'Enviando…' : 'Confirmar envío'}
      </button>
      {!preview && (
        <p className="text-xs text-gray-500">Generá una preview antes de enviar.</p>
      )}
    </div>
  )
}
