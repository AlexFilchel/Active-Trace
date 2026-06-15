import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useUmbral(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'umbral'],
    queryFn: () => comisionesService.getUmbral(comisionId!),
    enabled: !!comisionId,
    // default to 60% if config not found (404)
    select: (data) => data ?? { comision_id: comisionId!, umbral_pct: 60, valores_aprobatorios: [] },
  })
}
