import { apiClient } from '@/shared/services/api'
import type { Tarea, TareaCreate, TareaUpdate, Comentario, TareaEstado } from '../types'

function mapEstado(raw: string): TareaEstado {
  const map: Record<string, TareaEstado> = {
    'Pendiente': 'pendiente',
    'En Progreso': 'en_progreso',
    'Completada': 'completada',
  }
  return map[raw] ?? 'pendiente'
}

function mapTarea(item: any): Tarea {
  return {
    id: item.id,
    titulo: item.descripcion ?? '',
    descripcion: item.descripcion,
    estado: mapEstado(item.estado),
    asignado_a: item.asignado_a,
    prioridad: 'media',
    vencimiento: undefined,
    creado_en: item.created_at,
  }
}

export const tareasService = {
  async getTareas(): Promise<Tarea[]> {
    const res = await apiClient.get<any[]>('/api/tareas')
    return (res.data ?? []).map(mapTarea)
  },

  async createTarea(data: TareaCreate): Promise<Tarea> {
    const res = await apiClient.post<any>('/api/tareas', {
      descripcion: data.titulo,
      asignado_a: data.asignado_a,
    })
    return mapTarea(res.data)
  },

  async updateTarea(id: string, data: TareaUpdate): Promise<Tarea> {
    const estadoMap: Record<string, string> = {
      pendiente: 'Pendiente',
      en_progreso: 'En Progreso',
      completada: 'Completada',
    }
    const body: any = {}
    if (data.estado) body.estado = estadoMap[data.estado] ?? data.estado
    const res = await apiClient.put<any>(`/api/tareas/${id}/estado`, body)
    return mapTarea(res.data)
  },

  async deleteTarea(id: string): Promise<void> {
    await apiClient.delete(`/api/tareas/${id}`)
  },

  async getComentarios(id: string): Promise<Comentario[]> {
    const res = await apiClient.get<any[]>(`/api/tareas/${id}/comentarios`)
    return (res.data ?? []).map((c: any) => ({
      id: c.id,
      tarea_id: c.tarea_id,
      autor_id: c.autor_id,
      autor_nombre: c.autor_nombre ?? '',
      cuerpo: c.texto ?? c.cuerpo ?? '',
      creado_en: c.comentado_at ?? c.created_at,
    }))
  },

  async addComentario(id: string, cuerpo: string): Promise<Comentario> {
    const res = await apiClient.post<any>(`/api/tareas/${id}/comentarios`, { cuerpo })
    return {
      id: res.data.id,
      tarea_id: id,
      autor_id: res.data.autor_id,
      autor_nombre: res.data.autor_nombre ?? '',
      cuerpo: res.data.texto ?? res.data.cuerpo ?? '',
      creado_en: res.data.comentado_at ?? res.data.created_at,
    }
  },
}
