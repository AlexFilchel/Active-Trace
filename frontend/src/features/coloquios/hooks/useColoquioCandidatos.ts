import { useQuery } from '@tanstack/react-query'
import { coloquiosService } from '../services/coloquiosService'

export function useColoquioCandidatos(coloquioId: string | undefined) {
  return useQuery({
    queryKey: ['coloquios', coloquioId, 'candidatos'],
    queryFn: () => coloquiosService.getCandidatos(coloquioId!),
    enabled: !!coloquioId,
  })
}
