export type Periodo = string // e.g. "2024-06"

export type EstadoLiquidacion = 'ABIERTA' | 'CERRADA'

export type SegmentoLiquidacion = 'general' | 'nexo' | 'factura'

export interface LiquidacionKPIs {
  total_docentes: number
  total_honorarios: number
  estado: EstadoLiquidacion
  periodo: Periodo
}

export interface DetalleLiquidacion {
  id: string
  docente_nombre: string
  docente_email: string
  categoria: string
  horas: number
  salario_base: number
  total: number
  segmento: SegmentoLiquidacion
}

export interface Liquidacion {
  id: string
  periodo: Periodo
  estado: EstadoLiquidacion
  total_honorarios: number
  total_docentes: number
  detalles?: DetalleLiquidacion[]
}

export interface GrillaSalarial {
  id: string
  categoria: string
  salario_base: number
}

export interface GrillaSalarialCreate {
  categoria: string
  salario_base: number
}

export type EstadoFactura = 'PENDIENTE' | 'APROBADA' | 'RECHAZADA'

export interface Factura {
  id: string
  proveedor: string
  monto: number
  descripcion: string
  estado: EstadoFactura
  fecha: string
}

export interface FacturaCreate {
  proveedor: string
  monto: number
  descripcion: string
}
