export type AvisoScope = 'comision' | 'cohorte' | 'tenant'

export interface Aviso {
  id: string
  titulo: string
  cuerpo: string
  scope: AvisoScope
  scope_id?: string
  publicado: boolean
  creado_en: string
}

export interface AvisoCreate {
  titulo: string
  cuerpo: string
  scope: AvisoScope
  scope_id?: string
}

export interface Acknowledgment {
  alumno_id: string
  nombre: string
  apellido: string
  confirmado_en: string
}
