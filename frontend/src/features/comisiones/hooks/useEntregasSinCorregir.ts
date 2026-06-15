import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useEntregasSinCorregir(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'entregas-sin-corregir'],
    queryFn: () => comisionesService.getEntregasSinCorregir(comisionId!),
    enabled: !!comisionId,
  })
}
