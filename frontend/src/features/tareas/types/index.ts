export type TareaEstado = 'pendiente' | 'en_progreso' | 'completada'

export interface Tarea {
  id: string
  titulo: string
  descripcion?: string
  estado: TareaEstado
  asignado_a?: string
  prioridad: 'baja' | 'media' | 'alta'
  vencimiento?: string
  creado_en: string
}

export interface TareaCreate {
  titulo: string
  descripcion?: string
  asignado_a?: string
  prioridad?: 'baja' | 'media' | 'alta'
  vencimiento?: string
}

export interface TareaUpdate {
  titulo?: string
  descripcion?: string
  estado?: TareaEstado
  asignado_a?: string
  prioridad?: 'baja' | 'media' | 'alta'
  vencimiento?: string
}

export interface Comentario {
  id: string
  tarea_id: string
  autor_id: string
  autor_nombre: string
  cuerpo: string
  creado_en: string
}
