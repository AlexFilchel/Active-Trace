import { useQuery } from '@tanstack/react-query'
import { monitoresService } from '../services/monitoresService'
import type { MonitorFilter } from '../types'

export function useMonitorEntregas(filters?: MonitorFilter) {
  return useQuery({
    queryKey: ['monitores', 'entregas', filters],
    queryFn: () => monitoresService.getMonitorEntregas(filters),
  })
}
