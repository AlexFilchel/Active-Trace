import { useMutation, useQueryClient } from '@tanstack/react-query'
import { tareasService } from '../services/tareasService'
import type { TareaCreate } from '../types'

export function useCreateTarea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TareaCreate) => tareasService.createTarea(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tareas'] }),
  })
}
