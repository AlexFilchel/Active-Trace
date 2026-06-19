import { apiClient } from '@/shared/services/api'
import type { Equipo, MiembroEquipo, EquipoCreate, ClonarEquipoPayload, AltaMasivaPayload } from '../types'

function mapEquipo(item: any): Equipo {
  const nombre = item.materia_nombre
    ? `${item.materia_nombre} — ${item.rol_nombre ?? item.rol_id ?? ''}`
    : item.nombre ?? item.id
  return {
    id: item.id,
    nombre,
    descripcion: item.carrera_nombre
      ? `${item.carrera_nombre} / Cohorte ${item.cohorte_nombre ?? ''}`
      : item.descripcion,
    vigente: item.estado_vigencia === 'Vigente' || item.vigente === true,
    comision_id: item.comisiones?.[0] ?? undefined,
    cohorte_id: item.cohorte_id,
    creado_en: item.created_at ?? item.desde,
  }
}

export const equiposService = {
  async getEquipos(): Promise<Equipo[]> {
    const res = await apiClient.get<any[]>('/api/equipos/mis-equipos')
    return (res.data ?? []).map(mapEquipo)
  },

  async createEquipo(data: EquipoCreate): Promise<Equipo> {
    const res = await apiClient.post<any>('/api/equipos/asignaciones', data)
    return mapEquipo(res.data)
  },

  async updateEquipo(id: string, data: Partial<EquipoCreate>): Promise<Equipo> {
    const res = await apiClient.patch<any>(`/api/equipos/vigencia`, { id, ...data })
    return mapEquipo(res.data)
  },

  async deleteEquipo(id: string): Promise<void> {
    await apiClient.delete(`/api/equipos/asignaciones/${id}`)
  },

  async clonarEquipo(id: string, payload: ClonarEquipoPayload): Promise<Equipo> {
    const res = await apiClient.post<any>('/api/equipos/clonar', { origen_id: id, ...payload })
    return mapEquipo(res.data)
  },

  async altaMasiva(payload: AltaMasivaPayload): Promise<{ insertados: number }> {
    const res = await apiClient.post<{ insertados: number }>('/api/equipos/asignaciones/masiva', payload)
    return res.data
  },

  async getMiembros(_id: string): Promise<MiembroEquipo[]> {
    return []
  },

  async addMiembro(_id: string, _usuarioId: string): Promise<MiembroEquipo> {
    throw new Error('Not supported')
  },

  async removeMiembro(_id: string, _usuarioId: string): Promise<void> {},
}
