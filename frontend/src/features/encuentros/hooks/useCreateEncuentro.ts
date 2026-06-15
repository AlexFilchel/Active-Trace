import { useMutation, useQueryClient } from '@tanstack/react-query'
import { encuentrosService } from '../services/encuentrosService'
import type { EncuentroCreate } from '../types'

export function useCreateEncuentro() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: EncuentroCreate) => encuentrosService.createEncuentro(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['encuentros'] }),
  })
}
