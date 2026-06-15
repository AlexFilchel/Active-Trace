import { useMutation, useQueryClient } from '@tanstack/react-query'
import { equiposService } from '../services/equiposService'
import type { EquipoCreate } from '../types'

export function useCreateEquipo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: EquipoCreate) => equiposService.createEquipo(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipos'] }),
  })
}
