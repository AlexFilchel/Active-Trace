import { useMutation, useQueryClient } from '@tanstack/react-query'
import { tareasService } from '../services/tareasService'
import type { TareaUpdate } from '../types'

export function useUpdateTarea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TareaUpdate }) =>
      tareasService.updateTarea(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tareas'] }),
  })
}
