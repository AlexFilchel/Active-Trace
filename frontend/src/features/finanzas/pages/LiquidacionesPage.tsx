import { useState } from 'react'
import { useLiquidaciones } from '../hooks/useLiquidaciones'
import { useHistorialLiquidaciones } from '../hooks/useHistorialLiquidaciones'
import { useCerrarLiquidacion } from '../hooks/useCerrarLiquidacion'
import { useGrillasSalariales } from '../hooks/useGrillasSalariales'
import { useCrearGrilla } from '../hooks/useCrearGrilla'
import { useActualizarGrilla } from '../hooks/useActualizarGrilla'
import { useEliminarGrilla } from '../hooks/useEliminarGrilla'
import { useFacturas } from '../hooks/useFacturas'
import { useCrearFactura } from '../hooks/useCrearFactura'
import { useActualizarEstadoFactura } from '../hooks/useActualizarEstadoFactura'
import { KPIsLiquidacion } from '../components/KPIsLiquidacion'
import { TablaDetalleLiquidacion } from '../components/TablaDetalleLiquidacion'
import { HistorialLiquidaciones } from '../components/HistorialLiquidaciones'
import { GrillaSalarial } from '../components/GrillaSalarial'
import { TablaFacturas } from '../components/TablaFacturas'
import type { EstadoFactura, SegmentoLiquidacion } from '../types'

type MainTab = 'actual' | 'historial' | 'grilla' | 'facturas'
const CURRENT_PERIODO = new Date().toISOString().slice(0, 7) // "YYYY-MM"

export function LiquidacionesPage() {
  const [mainTab, setMainTab] = useState<MainTab>('actual')
  const [segmento, setSegmento] = useState<SegmentoLiquidacion>('general')

  const { data: liquidaciones = [], isLoading: loadingLiq } = useLiquidaciones(CURRENT_PERIODO)
  const { data: historial = [] } = useHistorialLiquidaciones()
  const { data: grillas = [] } = useGrillasSalariales()
  const { data: facturas = [] } = useFacturas()

  const cerrarMutation = useCerrarLiquidacion()
  const crearGrilla = useCrearGrilla()
  const actualizarGrilla = useActualizarGrilla()
  const eliminarGrilla = useEliminarGrilla()
  const crearFactura = useCrearFactura()
  const actualizarEstadoFactura = useActualizarEstadoFactura()

  const liquidacion = liquidaciones[0]

  const tabs: { id: MainTab; label: string }[] = [
    { id: 'actual', label: 'Liquidación Actual' },
    { id: 'historial', label: 'Historial' },
    { id: 'grilla', label: 'Grilla Salarial' },
    { id: 'facturas', label: 'Facturas' },
  ]

  const segmentos: { id: SegmentoLiquidacion; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'nexo', label: 'NEXO' },
    { id: 'factura', label: 'Factura' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Liquidaciones</h1>
        <span className="text-sm text-gray-500">Período: {CURRENT_PERIODO}</span>
      </div>

      {/* Main tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setMainTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              mainTab === t.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {mainTab === 'actual' && (
        <div>
          <KPIsLiquidacion liquidacion={liquidacion} isLoading={loadingLiq} />

          {liquidacion && liquidacion.estado === 'ABIERTA' && (
            <div className="mb-4 flex justify-end">
              <button
                onClick={() => cerrarMutation.mutate(liquidacion.id)}
                disabled={cerrarMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {cerrarMutation.isPending ? 'Cerrando…' : 'Cerrar liquidación'}
              </button>
            </div>
          )}

          {/* Segmento sub-tabs */}
          <div className="flex gap-2 mb-4">
            {segmentos.map((s) => (
              <button
                key={s.id}
                onClick={() => setSegmento(s.id)}
                className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                  segmento === s.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <TablaDetalleLiquidacion
            detalles={liquidacion?.detalles ?? []}
            segmento={segmento}
          />
        </div>
      )}

      {mainTab === 'historial' && (
        <HistorialLiquidaciones historial={historial} />
      )}

      {mainTab === 'grilla' && (
        <GrillaSalarial
          grillas={grillas}
          onCrear={(data) => crearGrilla.mutate(data)}
          onEditar={(id, data) => actualizarGrilla.mutate({ id, data })}
          onEliminar={(id) => eliminarGrilla.mutate(id)}
        />
      )}

      {mainTab === 'facturas' && (
        <TablaFacturas
          facturas={facturas}
          onCrear={(data) => crearFactura.mutate(data)}
          onCambiarEstado={(id, estado: EstadoFactura) => actualizarEstadoFactura.mutate({ id, estado })}
        />
      )}
    </div>
  )
}
