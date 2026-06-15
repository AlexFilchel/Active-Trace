import { useMutation, useQueryClient } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'

export function useCerrarLiquidacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => finanzasService.cerrarLiquidacion(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['liquidaciones'] })
    },
  })
}
