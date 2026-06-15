import { useQuery } from '@tanstack/react-query'
import { encuentrosService } from '../services/encuentrosService'

export function useGuardias() {
  return useQuery({
    queryKey: ['guardias'],
    queryFn: () => encuentrosService.getGuardias(),
  })
}
