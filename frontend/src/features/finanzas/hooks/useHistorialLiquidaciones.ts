import { useQuery } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'

export function useHistorialLiquidaciones() {
  return useQuery({
    queryKey: ['liquidaciones', 'historial'],
    queryFn: () => finanzasService.getHistorialLiquidaciones(),
  })
}
