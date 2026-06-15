import { apiClient } from '@/shared/services/api'
import type { Aviso, AvisoCreate, Acknowledgment } from '../types'

export const avisosService = {
  async getAvisos(): Promise<Aviso[]> {
    const res = await apiClient.get<Aviso[]>('/api/avisos')
    return res.data
  },

  async createAviso(data: AvisoCreate): Promise<Aviso> {
    const res = await apiClient.post<Aviso>('/api/avisos', data)
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
