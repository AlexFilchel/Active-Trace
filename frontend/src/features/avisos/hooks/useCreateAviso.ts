import { useMutation, useQueryClient } from '@tanstack/react-query'
import { avisosService } from '../services/avisosService'
import type { AvisoCreate } from '../types'

export function useCreateAviso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AvisoCreate) => avisosService.createAviso(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['avisos'] }),
  })
}
