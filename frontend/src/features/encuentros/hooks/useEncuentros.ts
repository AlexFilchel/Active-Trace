import { useQuery } from '@tanstack/react-query'
import { encuentrosService } from '../services/encuentrosService'

export function useEncuentros() {
  return useQuery({
    queryKey: ['encuentros'],
    queryFn: () => encuentrosService.getEncuentros(),
  })
}
