import { apiClient } from '@/shared/services/api'
import type { MonitorItem, EntregaMonitor, MonitorFilter } from '../types'

export const monitoresService = {
  async getMonitorGeneral(filters?: MonitorFilter): Promise<MonitorItem[]> {
    const params: Record<string, string> = {}
    if (filters?.comision_id) params.comision_id = filters.comision_id
    if (filters?.estado) params.estado = filters.estado
    const res = await apiClient.get<MonitorItem[]>('/api/alumnos/monitor', { params })
    return res.data
  },

  async getMonitorEntregas(filters?: MonitorFilter): Promise<EntregaMonitor[]> {
    const params: Record<string, string> = {}
    if (filters?.comision_id) params.comision_id = filters.comision_id
    const res = await apiClient.get<EntregaMonitor[]>('/api/calificaciones/entregas-sin-corregir', {
      params,
    })
    return res.data
  },
}
