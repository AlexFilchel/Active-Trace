import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useNotasFinales(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'notas-finales'],
    queryFn: () => comisionesService.getNotasFinales(comisionId!),
    enabled: !!comisionId,
  })
}
