import { apiClient } from '@/shared/services/api'
import type { MonitorItem, EntregaMonitor, MonitorFilter } from '../types'

export const monitoresService = {
  async getMonitorGeneral(_filters?: MonitorFilter): Promise<MonitorItem[]> {
    const res = await apiClient.get<{ items: any[] }>('/api/analisis/monitor')
    return (res.data.items ?? []).map((item: any) => ({
      alumno_id: item.entrada_padron_id,
      nombre: item.nombre,
      apellido: item.apellidos,
      legajo: item.comision ?? '',
      comision_id: item.comision ?? '',
      estado: item.estado,
      actividades_pendientes: item.actividades_pendientes ?? 0,
      ultimo_acceso: item.ultima_actividad_at,
    }))
  },

  async getMonitorEntregas(_filters?: MonitorFilter): Promise<EntregaMonitor[]> {
    const res = await apiClient.get<string>('/api/analisis/tps-sin-corregir/export', {
      responseType: 'text',
    })
    const csv: string = res.data ?? ''
    const lines = csv.trim().split('\n')
    if (lines.length < 2) return []
    return lines.slice(1).map((line, idx) => {
      const [nombre, apellido, materia, actividad, comision, , fecha_entrega] = line.split(',')
      return {
        alumno_id: `csv-${idx}`,
        nombre: nombre ?? '',
        apellido: apellido ?? '',
        legajo: comision ?? '',
        actividad_id: `act-${idx}`,
        actividad_nombre: `${actividad ?? ''} — ${materia ?? ''}`,
        comision_id: comision ?? '',
        fecha_entrega: fecha_entrega?.trim() ?? '',
      }
    })
  },
}
