import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'

export function useAtrasados() {
  return useQuery({
    queryKey: ['analisis', 'atrasados'],
    queryFn: () => comisionesService.getAtrasados(),
  })
}
