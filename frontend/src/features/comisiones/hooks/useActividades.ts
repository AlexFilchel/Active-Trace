import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useActividades(comisionId: ComisionId | undefined, tipo?: string) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'actividades', tipo],
    queryFn: () => comisionesService.getActividades(comisionId!, tipo),
    enabled: !!comisionId,
  })
}
