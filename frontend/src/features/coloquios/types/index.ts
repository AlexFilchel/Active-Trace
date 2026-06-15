export interface Coloquio {
  id: string
  materia: string
  comision_id: string
  fecha_convocatoria: string
  estado: 'abierto' | 'cerrado'
  creado_en: string
}

export interface ColoquioCreate {
  materia: string
  comision_id: string
  fecha_convocatoria: string
}

export interface ColoquioDia {
  id: string
  coloquio_id: string
  fecha: string
  cupo_maximo: number
  inscritos: number
}

export interface ColoquioDiaCreate {
  fecha: string
  cupo_maximo: number
}

export interface Candidato {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  dia_id?: string
  resultado?: 'aprobado' | 'desaprobado' | 'ausente'
}

export interface ResultadoPayload {
  resultado: 'aprobado' | 'desaprobado' | 'ausente'
}
