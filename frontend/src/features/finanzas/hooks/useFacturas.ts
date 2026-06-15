import { useQuery } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'

export function useFacturas() {
  return useQuery({
    queryKey: ['facturas'],
    queryFn: () => finanzasService.getFacturas(),
  })
}
