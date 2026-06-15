import { useQuery } from '@tanstack/react-query'
import { finanzasService } from '../services/finanzasService'

export function useGrillasSalariales() {
  return useQuery({
    queryKey: ['grillas-salariales'],
    queryFn: () => finanzasService.getGrillasSalariales(),
  })
}
