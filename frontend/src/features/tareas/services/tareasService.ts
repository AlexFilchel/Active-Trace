import { apiClient } from '@/shared/services/api'
import type { Tarea, TareaCreate, TareaUpdate, Comentario } from '../types'

export const tareasService = {
  async getTareas(): Promise<Tarea[]> {
    const res = await apiClient.get<Tarea[]>('/api/tareas')
    return res.data
  },

  async createTarea(data: TareaCreate): Promise<Tarea> {
    const res = await apiClient.post<Tarea>('/api/tareas', data)
    return res.data
  },

  async updateTarea(id: string, data: TareaUpdate): Promise<Tarea> {
    const res = await apiClient.put<Tarea>(`/api/tareas/${id}`, data)
    return res.data
  },

  async deleteTarea(id: string): Promise<void> {
    await apiClient.delete(`/api/tareas/${id}`)
  },

  async getComentarios(id: string): Promise<Comentario[]> {
    const res = await apiClient.get<Comentario[]>(`/api/tareas/${id}/comentarios`)
    return res.data
  },

  async addComentario(id: string, cuerpo: string): Promise<Comentario> {
    const res = await apiClient.post<Comentario>(`/api/tareas/${id}/comentarios`, { cuerpo })
    return res.data
  },
}
