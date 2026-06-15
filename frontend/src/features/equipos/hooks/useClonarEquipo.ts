import { useMutation, useQueryClient } from '@tanstack/react-query'
import { equiposService } from '../services/equiposService'
import type { ClonarEquipoPayload } from '../types'

export function useClonarEquipo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ClonarEquipoPayload }) =>
      equiposService.clonarEquipo(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipos'] }),
  })
}
