import { apiClient } from '@/shared/services/api'
import type { Encuentro, EncuentroCreate, Guardia, GuardiaCreate } from '../types'

export const encuentrosService = {
  async getEncuentros(): Promise<Encuentro[]> {
    const res = await apiClient.get<Encuentro[]>('/api/encuentros')
    return res.data
  },

  async createEncuentro(data: EncuentroCreate): Promise<Encuentro> {
    const res = await apiClient.post<Encuentro>('/api/encuentros', data)
    return res.data
  },

  async updateEncuentro(id: string, data: Partial<EncuentroCreate>): Promise<Encuentro> {
    const res = await apiClient.put<Encuentro>(`/api/encuentros/${id}`, data)
    return res.data
  },

  async deleteEncuentro(id: string): Promise<void> {
    await apiClient.delete(`/api/encuentros/${id}`)
  },

  async getGuardias(): Promise<Guardia[]> {
    const res = await apiClient.get<Guardia[]>('/api/guardias')
    return res.data
  },

  async createGuardia(data: GuardiaCreate): Promise<Guardia> {
    const res = await apiClient.post<Guardia>('/api/guardias', data)
    return res.data
  },
}
