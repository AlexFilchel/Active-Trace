import { useQuery } from '@tanstack/react-query'
import { coloquiosService } from '../services/coloquiosService'

export function useColoquioDias(coloquioId: string | undefined) {
  return useQuery({
    queryKey: ['coloquios', coloquioId, 'dias'],
    queryFn: () => coloquiosService.getDias(coloquioId!),
    enabled: !!coloquioId,
  })
}
