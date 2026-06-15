// ── Domain types for the comisiones feature ─────────────────────────────────

export type ComisionId = string

export interface Actividad {
  id: string
  nombre: string
  tipo: string
  fecha_entrega?: string
}

export interface UmbralConfig {
  comision_id: ComisionId
  umbral_pct: number
  valores_aprobatorios: number[]
}

export interface AlumnoAtrasado {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  actividades_pendientes: string[]
  motivo: string
}

export interface RankingItem {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  promedio: number
  posicion: number
}

export interface NotaFinal {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  nota_final: number | null
  estado: string
}

export interface EntregaSinCorregir {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  actividad_id: string
  actividad_nombre: string
  fecha_entrega: string
}

export interface ReporteRapido {
  total_alumnos: number
  aprobados: number
  reprobados: number
  sin_nota: number
  atrasados: number
  promedio_general: number | null
}

export type EstadoComunicacion = 'Pendiente' | 'Enviando' | 'OK' | 'Fallido' | 'Cancelado'

export interface EstadoDestinatario {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  estado: EstadoComunicacion
  error?: string
}

export interface ComunicacionPreview {
  asunto: string
  cuerpo: string
  destinatarios_count: number
}

export interface ImportacionResult {
  importados: number
  errores: number
  detalle?: string
}

export interface CalificacionImport {
  alumno_id: string
  actividad_id: string
  nota: number
}
