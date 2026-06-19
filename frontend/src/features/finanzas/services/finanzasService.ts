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
    const res = await apiClient.get<any[]>('/api/liquidaciones', { params: { periodo } })
    const items: any[] = res.data ?? []
    if (items.length === 0) return []
    const totalHonorarios = items.reduce((sum, i) => sum + parseFloat(i.total ?? 0), 0)
    const estadoRaw: string = items[0]?.estado ?? 'Abierta'
    return [{
      id: items[0].id,
      periodo: items[0].periodo,
      estado: estadoRaw.toUpperCase() === 'ABIERTA' || estadoRaw === 'Abierta' ? 'ABIERTA' : 'CERRADA',
      total_honorarios: totalHonorarios,
      total_docentes: items.length,
    }]
  },

  async calcularLiquidacion(periodo: Periodo): Promise<Liquidacion> {
    const res = await apiClient.post<any>('/api/liquidaciones/calcular', { periodo })
    return {
      id: res.data.id,
      periodo: res.data.periodo,
      estado: 'ABIERTA',
      total_honorarios: parseFloat(res.data.total ?? 0),
      total_docentes: 1,
    }
  },

  async cerrarLiquidacion(id: string): Promise<Liquidacion> {
    const res = await apiClient.put<any>(`/api/liquidaciones/${id}/cerrar`, {})
    return {
      id: res.data.id,
      periodo: res.data.periodo,
      estado: 'CERRADA',
      total_honorarios: parseFloat(res.data.total ?? 0),
      total_docentes: 1,
    }
  },

  async getDetalleLiquidacion(_id: string): Promise<Liquidacion> {
    return { id: _id, periodo: '', estado: 'ABIERTA', total_honorarios: 0, total_docentes: 0 }
  },

  async getHistorialLiquidaciones(): Promise<Liquidacion[]> {
    const res = await apiClient.get<any>('/api/liquidaciones/historial')
    const items: any[] = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
    return items.map((i: any) => ({
      id: i.id,
      periodo: i.periodo,
      estado: (i.estado === 'Abierta' ? 'ABIERTA' : 'CERRADA') as 'ABIERTA' | 'CERRADA',
      total_honorarios: parseFloat(i.total ?? 0),
      total_docentes: 1,
    }))
  },

  // ── Grilla Salarial ────────────────────────────────────────────────────────

  async getGrillasSalariales(): Promise<GrillaSalarial[]> {
    const res = await apiClient.get<any[]>('/api/salarios/base')
    return (res.data ?? []).map((item: any) => ({
      id: item.id,
      categoria: item.rol,
      salario_base: parseFloat(item.monto ?? 0),
    }))
  },

  async crearGrilla(data: GrillaSalarialCreate): Promise<GrillaSalarial> {
    const res = await apiClient.post<any>('/api/salarios/base', {
      rol: data.categoria,
      monto: data.salario_base,
      desde: new Date().toISOString().slice(0, 10),
    })
    return { id: res.data.id, categoria: res.data.rol, salario_base: parseFloat(res.data.monto) }
  },

  async actualizarGrilla(id: string, data: GrillaSalarialCreate): Promise<GrillaSalarial> {
    const res = await apiClient.put<any>(`/api/salarios/base/${id}`, {
      rol: data.categoria,
      monto: data.salario_base,
    })
    return { id: res.data.id, categoria: res.data.rol, salario_base: parseFloat(res.data.monto) }
  },

  async eliminarGrilla(id: string): Promise<void> {
    await apiClient.delete(`/api/salarios/base/${id}`)
  },

  // ── Facturas ───────────────────────────────────────────────────────────────

  async getFacturas(): Promise<Factura[]> {
    const res = await apiClient.get<any[]>('/api/facturas')
    return (res.data ?? []).map((item: any) => ({
      id: item.id,
      proveedor: item.usuario_id,
      monto: parseFloat(item.monto ?? 0),
      descripcion: item.detalle ?? '',
      estado: (item.estado?.toUpperCase() ?? 'PENDIENTE') as EstadoFactura,
      fecha: item.cargada_at ?? item.created_at,
    }))
  },

  async crearFactura(data: FacturaCreate): Promise<Factura> {
    const res = await apiClient.post<any>('/api/facturas', data)
    return {
      id: res.data.id,
      proveedor: data.proveedor,
      monto: data.monto,
      descripcion: data.descripcion,
      estado: 'PENDIENTE',
      fecha: res.data.created_at,
    }
  },

  async actualizarEstadoFactura(id: string, estado: EstadoFactura): Promise<Factura> {
    const res = await apiClient.put<any>(`/api/facturas/${id}/abonar`, { estado })
    return {
      id: res.data.id,
      proveedor: '',
      monto: 0,
      descripcion: '',
      estado,
      fecha: res.data.updated_at,
    }
  },
}
