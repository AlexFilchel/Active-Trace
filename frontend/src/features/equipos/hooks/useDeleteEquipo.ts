import { useMutation, useQueryClient } from '@tanstack/react-query'
import { equiposService } from '../services/equiposService'

export function useDeleteEquipo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => equiposService.deleteEquipo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipos'] }),
  })
}
