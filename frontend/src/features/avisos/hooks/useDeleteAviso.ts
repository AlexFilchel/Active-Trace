import { useMutation, useQueryClient } from '@tanstack/react-query'
import { avisosService } from '../services/avisosService'

export function useDeleteAviso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => avisosService.deleteAviso(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['avisos'] }),
  })
}
