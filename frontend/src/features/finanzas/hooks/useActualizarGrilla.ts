import { useMutation, useQueryClient } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'
import type { GrillaSalarialCreate } from '../types'

export function useActualizarGrilla() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GrillaSalarialCreate }) =>
      finanzasService.actualizarGrilla(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['grillas-salariales'] })
    },
  })
}
