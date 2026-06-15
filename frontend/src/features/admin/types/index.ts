// ── Estructura académica ───────────────────────────────────────────────────

export interface Carrera {
  id: string
  nombre: string
  codigo?: string
  descripcion?: string
}

export interface CarreraCreate {
  nombre: string
  codigo?: string
  descripcion?: string
}

export interface Cohorte {
  id: string
  nombre: string
  carrera_id: string
  anio: number
}

export interface CohorteCreate {
  nombre: string
  carrera_id: string
  anio: number
}

export interface Materia {
  id: string
  nombre: string
  codigo?: string
  carrera_id: string
}

export interface MateriaCreate {
  nombre: string
  codigo?: string
  carrera_id: string
}

// ── Usuarios ───────────────────────────────────────────────────────────────

export type RolUsuario = 'ALUMNO' | 'TUTOR' | 'PROFESOR' | 'COORDINADOR' | 'NEXO' | 'ADMIN' | 'FINANZAS'

export interface Usuario {
  id: string
  nombre: string
  apellido: string
  email: string
  roles: RolUsuario[]
  activo: boolean
}

export interface UsuarioCreate {
  nombre: string
  apellido: string
  email: string
  password: string
  roles: RolUsuario[]
}

export interface UsuarioUpdate {
  nombre?: string
  apellido?: string
  email?: string
  activo?: boolean
}

// ── Auditoría ──────────────────────────────────────────────────────────────

export interface AuditoriaEntry {
  id: string
  accion: string
  usuario_email: string
  modulo: string
  detalle?: string
  timestamp: string
}

export interface AuditoriaFiltros {
  accion?: string
  usuario?: string
  desde?: string
  hasta?: string
  modulo?: string
}

export interface AuditoriaMetricas {
  total_eventos_hoy: number
  total_eventos_semana: number
  acciones_frecuentes: { accion: string; count: number }[]
  usuarios_activos_hoy: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
