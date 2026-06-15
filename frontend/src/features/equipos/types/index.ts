export interface Equipo {
  id: string
  nombre: string
  descripcion?: string
  vigente: boolean
  comision_id?: string
  cohorte_id?: string
  creado_en: string
}

export interface MiembroEquipo {
  usuario_id: string
  nombre: string
  apellido: string
  email: string
  rol: string
}

export interface EquipoCreate {
  nombre: string
  descripcion?: string
  comision_id?: string
  cohorte_id?: string
}

export interface ClonarEquipoPayload {
  nombre: string
  comision_id?: string
}

export interface AltaMasivaPayload {
  equipo_id: string
  usuario_ids: string[]
}
