import { apiClient } from '@/shared/services/api'
import type {
  Liquidacion,
  GrillaSalarial,
  GrillaSalarialCreate,
  Factura,
  FacturaCreate,
  EstadoFactura,
  Periodo,
} from '../types'

export const finanzasService = {
  // ── Liquidaciones ──────────────────────────────────────────────────────────

  async getLiquidaciones(periodo: Periodo): Promise<Liquidacion[]> {
    const res = await apiClient.get<Liquidacion[]>('/api/liquidaciones', {
      params: { periodo },
    })
    return res.data
  },

  async calcularLiquidacion(periodo: Periodo): Promise<Liquidacion> {
    const res = await apiClient.post<Liquidacion>('/api/liquidaciones/calcular', { periodo })
    return res.data
  },

  async cerrarLiquidacion(id: string): Promise<Liquidacion> {
    const res = await apiClient.put<Liquidacion>(`/api/liquidaciones/${id}/cerrar`, {})
    return res.data
  },

  async getDetalleLiquidacion(id: string): Promise<Liquidacion> {
    const res = await apiClient.get<Liquidacion>(`/api/liquidaciones/${id}/detalle`)
    return res.data
  },

  async getHistorialLiquidaciones(): Promise<Liquidacion[]> {
    const res = await apiClient.get<Liquidacion[]>('/api/liquidaciones/historial')
    return res.data
  },

  // ── Grilla Salarial ────────────────────────────────────────────────────────

  async getGrillasSalariales(): Promise<GrillaSalarial[]> {
    const res = await apiClient.get<GrillaSalarial[]>('/api/salarios/grilla')
    return res.data
  },

  async crearGrilla(data: GrillaSalarialCreate): Promise<GrillaSalarial> {
    const res = await apiClient.post<GrillaSalarial>('/api/salarios/grilla', data)
    return res.data
  },

  async actualizarGrilla(id: string, data: GrillaSalarialCreate): Promise<GrillaSalarial> {
    const res = await apiClient.put<GrillaSalarial>(`/api/salarios/grilla/${id}`, data)
    return res.data
  },

  async eliminarGrilla(id: string): Promise<void> {
    await apiClient.delete(`/api/salarios/grilla/${id}`)
  },

  // ── Facturas ───────────────────────────────────────────────────────────────

  async getFacturas(): Promise<Factura[]> {
    const res = await apiClient.get<Factura[]>('/api/facturas')
    return res.data
  },

  async crearFactura(data: FacturaCreate): Promise<Factura> {
    const res = await apiClient.post<Factura>('/api/facturas', data)
    return res.data
  },

  async actualizarEstadoFactura(id: string, estado: EstadoFactura): Promise<Factura> {
    const res = await apiClient.put<Factura>(`/api/facturas/${id}/estado`, { estado })
    return res.data
  },
}
