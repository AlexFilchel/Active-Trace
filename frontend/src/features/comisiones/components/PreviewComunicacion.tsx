import type { ComunicacionPreview } from '../types'

interface Props {
  preview?: ComunicacionPreview
  error?: string
  onEnviar?: () => void
  isSending?: boolean
}

export function PreviewComunicacion({ preview, error, onEnviar, isSending }: Props) {
  if (error) {
    return (
      <div role="alert" className="rounded-md bg-red-50 p-4 text-sm text-red-800">
        {error}
        <p className="mt-1 text-xs">No se puede enviar la comunicación hasta resolver el error.</p>
      </div>
    )
  }

  if (!preview) {
    return (
      <p className="text-sm text-gray-500 italic">
        Generá una preview para ver el contenido antes de enviar.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
        <div>
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Asunto</span>
          <p className="text-sm text-gray-800">{preview.asunto}</p>
        </div>
        <div>
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Cuerpo</span>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{preview.cuerpo}</p>
        </div>
        <p className="text-xs text-gray-500">
          Destinatarios: <span className="font-medium">{preview.destinatarios_count}</span>
        </p>
      </div>
      <button
        onClick={onEnviar}
        disabled={isSending}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isSending ? 'Enviando…' : 'Enviar comunicación'}
      </button>
    </div>
  )
}
