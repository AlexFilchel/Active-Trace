import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useAtrasados(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'atrasados'],
    queryFn: () => comisionesService.getAtrasados(comisionId!),
    enabled: !!comisionId,
  })
}
