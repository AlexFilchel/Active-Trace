import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'

export function useRanking() {
  return useQuery({
    queryKey: ['analisis', 'ranking'],
    queryFn: () => comisionesService.getRanking(),
  })
}
