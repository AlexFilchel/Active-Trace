import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'

export function useNotasFinales() {
  return useQuery({
    queryKey: ['analisis', 'notas-finales'],
    queryFn: () => comisionesService.getNotasFinales(),
  })
}
