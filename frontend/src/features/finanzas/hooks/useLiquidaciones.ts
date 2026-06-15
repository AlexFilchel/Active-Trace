import { useQuery } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'
import type { Periodo } from '../types'

export function useLiquidaciones(periodo: Periodo | undefined) {
  return useQuery({
    queryKey: ['liquidaciones', periodo],
    queryFn: () => finanzasService.getLiquidaciones(periodo!),
    enabled: !!periodo,
  })
}
