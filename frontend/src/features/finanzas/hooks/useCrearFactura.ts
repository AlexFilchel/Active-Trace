import { useMutation, useQueryClient } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'
import type { FacturaCreate } from '../types'

export function useCrearFactura() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: FacturaCreate) => finanzasService.crearFactura(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['facturas'] })
    },
  })
}
