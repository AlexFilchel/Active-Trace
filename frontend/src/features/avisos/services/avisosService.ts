import { apiClient } from '@/shared/services/api'
import type { Aviso, AvisoCreate, Acknowledgment } from '../types'

export const avisosService = {
  async getAvisos(): Promise<Aviso[]> {
    const res = await apiClient.get<any[]>('/api/avisos/gestion')
    return (res.data ?? []).map((item: any) => ({
      id: item.id,
      titulo: item.titulo,
      cuerpo: item.cuerpo,
      scope: item.alcance === 'General' ? 'tenant' : item.alcance === 'Materia' ? 'comision' : 'cohorte',
      scope_id: item.materia_id ?? item.cohorte_id ?? undefined,
      publicado: item.activo ?? true,
      creado_en: item.created_at,
    }))
  },

  async createAviso(data: AvisoCreate): Promise<Aviso> {
    const res = await apiClient.post<Aviso>('/api/avisos/gestion', data)
    return res.data
  },

  async updateAviso(id: string, data: Partial<AvisoCreate>): Promise<Aviso> {
    const res = await apiClient.put<Aviso>(`/api/avisos/${id}`, data)
    return res.data
  },

  async deleteAviso(id: string): Promise<void> {
    await apiClient.delete(`/api/avisos/${id}`)
  },

  async getAcknowledgments(id: string): Promise<Acknowledgment[]> {
    const res = await apiClient.get<Acknowledgment[]>(`/api/avisos/${id}/acknowledgments`)
    return res.data
  },
}
