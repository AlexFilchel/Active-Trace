import { apiClient } from '@/shared/services/api'
import type { Equipo, MiembroEquipo, EquipoCreate, ClonarEquipoPayload, AltaMasivaPayload } from '../types'

export const equiposService = {
  async getEquipos(): Promise<Equipo[]> {
    const res = await apiClient.get<Equipo[]>('/api/equipos')
    return res.data
  },

  async createEquipo(data: EquipoCreate): Promise<Equipo> {
    const res = await apiClient.post<Equipo>('/api/equipos', data)
    return res.data
  },

  async updateEquipo(id: string, data: Partial<EquipoCreate>): Promise<Equipo> {
    const res = await apiClient.put<Equipo>(`/api/equipos/${id}`, data)
    return res.data
  },

  async deleteEquipo(id: string): Promise<void> {
    await apiClient.delete(`/api/equipos/${id}`)
  },

  async clonarEquipo(id: string, payload: ClonarEquipoPayload): Promise<Equipo> {
    const res = await apiClient.post<Equipo>(`/api/equipos/${id}/clonar`, payload)
    return res.data
  },

  async altaMasiva(payload: AltaMasivaPayload): Promise<{ insertados: number }> {
    const res = await apiClient.post<{ insertados: number }>('/api/equipos/masivo', payload)
    return res.data
  },

  async getMiembros(id: string): Promise<MiembroEquipo[]> {
    const res = await apiClient.get<MiembroEquipo[]>(`/api/equipos/${id}/miembros`)
    return res.data
  },

  async addMiembro(id: string, usuarioId: string): Promise<MiembroEquipo> {
    const res = await apiClient.post<MiembroEquipo>(`/api/equipos/${id}/miembros`, {
      usuario_id: usuarioId,
    })
    return res.data
  },

  async removeMiembro(id: string, usuarioId: string): Promise<void> {
    await apiClient.delete(`/api/equipos/${id}/miembros/${usuarioId}`)
  },
}
