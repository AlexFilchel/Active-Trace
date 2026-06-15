export interface Encuentro {
  id: string
  titulo: string
  fecha: string
  hora_inicio: string
  hora_fin: string
  aula?: string
  comision_id: string
  tipo: 'clase' | 'tutoría' | 'otro'
}

export interface EncuentroCreate {
  titulo: string
  fecha: string
  hora_inicio: string
  hora_fin: string
  aula?: string
  comision_id: string
  tipo: 'clase' | 'tutoría' | 'otro'
}

export interface Guardia {
  id: string
  tutor_id: string
  tutor_nombre: string
  fecha: string
  hora_inicio: string
  hora_fin: string
}

export interface GuardiaCreate {
  tutor_id: string
  fecha: string
  hora_inicio: string
  hora_fin: string
}
