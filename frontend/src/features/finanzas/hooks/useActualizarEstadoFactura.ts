import { useMutation, useQueryClient } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'
import type { EstadoFactura } from '../types'

export function useActualizarEstadoFactura() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: EstadoFactura }) =>
      finanzasService.actualizarEstadoFactura(id, estado),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['facturas'] })
    },
  })
}
