import { useQuery } from '@tanstack/react-query'
import { monitoresService } from '../services/monitoresService'
import type { MonitorFilter } from '../types'

export function useMonitorGeneral(filters?: MonitorFilter) {
  return useQuery({
    queryKey: ['monitores', 'general', filters],
    queryFn: () => monitoresService.getMonitorGeneral(filters),
  })
}
