import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'

export function useEntregasSinCorregir() {
  return useQuery({
    queryKey: ['analisis', 'entregas-sin-corregir'],
    queryFn: () => comisionesService.getEntregasSinCorregir(),
  })
}
