import { useMutation, useQueryClient } from '@tanstack/react-query'
import { tareasService } from '../services/tareasService'

export function useDeleteTarea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => tareasService.deleteTarea(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tareas'] }),
  })
}
