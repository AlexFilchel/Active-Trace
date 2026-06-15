import type { EntregaSinCorregir } from '../types'

/**
 * Generates a CSV download from a list of EntregaSinCorregir via a temporary Blob URL.
 * Pure utility — no React component needed; called from TablaEntregasSinCorregir.
 */
export function exportarEntregas(entregas: EntregaSinCorregir[], filename = 'entregas-sin-corregir.csv'): void {
  const header = 'legajo,apellido,nombre,actividad,fecha_entrega'
  const rows = entregas.map(
    (e) => `${e.legajo},${e.apellido},${e.nombre},${e.actividad_nombre},${e.fecha_entrega}`,
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
