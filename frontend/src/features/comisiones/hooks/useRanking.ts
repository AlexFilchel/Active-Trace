import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useRanking(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'ranking'],
    queryFn: () => comisionesService.getRanking(comisionId!),
    enabled: !!comisionId,
  })
}
