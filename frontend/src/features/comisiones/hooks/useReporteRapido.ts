import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useReporteRapido(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'reporte-rapido'],
    queryFn: () => comisionesService.getReporteRapido(comisionId!),
    enabled: !!comisionId,
  })
}
