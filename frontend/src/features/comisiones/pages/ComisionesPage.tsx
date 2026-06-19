import { useState } from 'react'
import { useActividades } from '../hooks/useActividades'
import { useUmbral } from '../hooks/useUmbral'
import { useAtrasados } from '../hooks/useAtrasados'
import { useRanking } from '../hooks/useRanking'
import { useNotasFinales } from '../hooks/useNotasFinales'
import { useReporteRapido } from '../hooks/useReporteRapido'
import { useEntregasSinCorregir } from '../hooks/useEntregasSinCorregir'
import { useComunicacionesEstado } from '../hooks/useComunicacionesEstado'
import { useImportarCalificaciones } from '../hooks/useImportarCalificaciones'
import { useActualizarUmbral } from '../hooks/useActualizarUmbral'
import { usePreviewComunicacion } from '../hooks/usePreviewComunicacion'
import { useEnviarComunicacion } from '../hooks/useEnviarComunicacion'
import { ImportadorCalificaciones } from '../components/ImportadorCalificaciones'
import { ConfiguradorUmbral } from '../components/ConfiguradorUmbral'
import { TablaAtrasados } from '../components/TablaAtrasados'
import { TablaRanking } from '../components/TablaRanking'
import { TablaNotasFinales } from '../components/TablaNotasFinales'
import { ReporteRapido } from '../components/ReporteRapido'
import { TablaEntregasSinCorregir } from '../components/TablaEntregasSinCorregir'
import { MonitorSeguimiento } from '../components/MonitorSeguimiento'
import { PreviewComunicacion } from '../components/PreviewComunicacion'
import { PanelEnvioComunicacion } from '../components/PanelEnvioComunicacion'
import { PanelEstadoComunicaciones } from '../components/PanelEstadoComunicaciones'
import { exportarEntregas } from '../components/ExportarEntregas'
import type { ComisionId, ImportacionResult } from '../types'

type Tab = 'importacion' | 'analisis' | 'comunicacion'

export function ComisionesPage() {
  const [comisionId, setComisionId] = useState<ComisionId>('')
  const [activeTab, setActiveTab] = useState<Tab>('importacion')

  const selectedId = comisionId || undefined

  // Data queries
  const { data: actividades = [] } = useActividades(selectedId)
  const { data: umbral } = useUmbral(selectedId)
  const { data: atrasados = [] } = useAtrasados()
  const { data: ranking = [] } = useRanking()
  const { data: notas = [] } = useNotasFinales()
  const { data: reporte } = useReporteRapido()
  const { data: entregas = [] } = useEntregasSinCorregir()
  const { data: estadoComunicaciones = [] } = useComunicacionesEstado(selectedId)

  // Mutations
  const importar = useImportarCalificaciones()
  const actualizarUmbral = useActualizarUmbral()
  const previewMutation = usePreviewComunicacion()
  const enviarMutation = useEnviarComunicacion()

  async function handleImport(file: File, activs: string[]): Promise<ImportacionResult> {
    return importar.mutateAsync({ comisionId: comisionId, file, actividades: activs })
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: 'importacion', label: 'Importación' },
    { id: 'analisis', label: 'Análisis' },
    { id: 'comunicacion', label: 'Comunicación' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-gray-800">Comisiones</h1>
        <div>
          <label htmlFor="comision-select" className="sr-only">
            Comisión
          </label>
          <input
            id="comision-select"
            type="text"
            value={comisionId}
            onChange={(e) => setComisionId(e.target.value)}
            placeholder="ID de comisión…"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Tab bar */}
          <div className="flex border-b border-gray-200">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === tab.id
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === 'importacion' && (
            <div className="space-y-6">
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Importar calificaciones</h2>
                <ImportadorCalificaciones
                  actividades={actividades}
                  onImport={handleImport}
                  isLoading={importar.isPending}
                />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Umbral de aprobación</h2>
                <ConfiguradorUmbral
                  current={umbral}
                  onSave={(pct) =>
                    actualizarUmbral.mutate({
                      comisionId,
                      umbralPct: pct,
                      valoresAprobatorios: umbral?.valores_aprobatorios ?? [],
                    })
                  }
                  isSaving={actualizarUmbral.isPending}
                />
              </section>
            </div>
          )}

          {activeTab === 'analisis' && (
            <div className="space-y-6">
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Reporte rápido</h2>
                <ReporteRapido reporte={reporte} />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Alumnos atrasados</h2>
                <TablaAtrasados atrasados={atrasados} />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Monitor de seguimiento</h2>
                <MonitorSeguimiento atrasados={atrasados} />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Ranking</h2>
                <TablaRanking ranking={ranking} />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Notas finales</h2>
                <TablaNotasFinales notas={notas} />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Entregas sin corregir</h2>
                <TablaEntregasSinCorregir
                  entregas={entregas}
                  onExport={() => exportarEntregas(entregas)}
                />
              </section>
            </div>
          )}

          {activeTab === 'comunicacion' && (
            <div className="space-y-6">
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Preview</h2>
                <button
                  onClick={() => previewMutation.mutate({ comisionId, tipo: 'atraso' })}
                  disabled={previewMutation.isPending}
                  className="mb-3 rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
                >
                  Generar preview
                </button>
                <PreviewComunicacion
                  preview={previewMutation.data}
                  error={previewMutation.isError ? 'Error al generar preview' : undefined}
                  onEnviar={() =>
                    enviarMutation.mutate({ comisionId, tipo: 'atraso' })
                  }
                  isSending={enviarMutation.isPending}
                />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Enviar con mensaje personalizado</h2>
                <PanelEnvioComunicacion
                  preview={previewMutation.data}
                  onConfirm={(msg) =>
                    enviarMutation.mutate({ comisionId, tipo: 'atraso', mensajePersonalizado: msg })
                  }
                  isSending={enviarMutation.isPending}
                />
              </section>
              <section>
                <h2 className="text-base font-medium text-gray-700 mb-3">Estado de envíos</h2>
                <PanelEstadoComunicaciones estados={estadoComunicaciones} />
              </section>
            </div>
          )}
    </div>
  )
}
