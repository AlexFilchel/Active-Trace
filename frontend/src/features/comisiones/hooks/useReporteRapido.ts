import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'

export function useReporteRapido() {
  return useQuery({
    queryKey: ['analisis', 'reporte-rapido'],
    queryFn: () => comisionesService.getReporteRapido(),
  })
}
