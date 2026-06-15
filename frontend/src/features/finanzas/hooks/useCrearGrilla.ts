import { useMutation, useQueryClient } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'
import type { GrillaSalarialCreate } from '../types'

export function useCrearGrilla() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GrillaSalarialCreate) => finanzasService.crearGrilla(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['grillas-salariales'] })
    },
  })
}
