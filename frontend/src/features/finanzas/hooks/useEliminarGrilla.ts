import { useMutation, useQueryClient } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'

export function useEliminarGrilla() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => finanzasService.eliminarGrilla(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['grillas-salariales'] })
    },
  })
}
