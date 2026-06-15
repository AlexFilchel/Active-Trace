import { apiClient } from '@/shared/services/api'
import type {
  Coloquio,
  ColoquioCreate,
  ColoquioDia,
  ColoquioDiaCreate,
  Candidato,
  ResultadoPayload,
} from '../types'

export const coloquiosService = {
  async getColoquios(): Promise<Coloquio[]> {
    const res = await apiClient.get<Coloquio[]>('/api/coloquios')
    return res.data
  },

  async createColoquio(data: ColoquioCreate): Promise<Coloquio> {
    const res = await apiClient.post<Coloquio>('/api/coloquios', data)
    return res.data
  },

  async getDias(id: string): Promise<ColoquioDia[]> {
    const res = await apiClient.get<ColoquioDia[]>(`/api/coloquios/${id}/dias`)
    return res.data
  },

  async addDia(id: string, data: ColoquioDiaCreate): Promise<ColoquioDia> {
    const res = await apiClient.post<ColoquioDia>(`/api/coloquios/${id}/dias`, data)
    return res.data
  },

  async getCandidatos(id: string): Promise<Candidato[]> {
    const res = await apiClient.get<Candidato[]>(`/api/coloquios/${id}/candidatos`)
    return res.data
  },

  async addCandidato(id: string, alumnoId: string): Promise<Candidato> {
    const res = await apiClient.post<Candidato>(`/api/coloquios/${id}/candidatos`, {
      alumno_id: alumnoId,
    })
    return res.data
  },

  async reservar(id: string, diaId: string, alumnoId: string): Promise<Candidato> {
    const res = await apiClient.post<Candidato>(
      `/api/coloquios/${id}/dias/${diaId}/reservar`,
      { alumno_id: alumnoId },
    )
    return res.data
  },

  async setResultado(
    id: string,
    alumnoId: string,
    payload: ResultadoPayload,
  ): Promise<Candidato> {
    const res = await apiClient.put<Candidato>(
      `/api/coloquios/${id}/candidatos/${alumnoId}/resultado`,
      payload,
    )
    return res.data
  },
}
