export interface MonitorItem {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  comision_id: string
  estado: string
  actividades_pendientes: number
  ultimo_acceso?: string
}

export interface EntregaMonitor {
  alumno_id: string
  nombre: string
  apellido: string
  legajo: string
  actividad_id: string
  actividad_nombre: string
  comision_id: string
  fecha_entrega: string
}

export interface MonitorFilter {
  comision_id?: string
  estado?: string
}
