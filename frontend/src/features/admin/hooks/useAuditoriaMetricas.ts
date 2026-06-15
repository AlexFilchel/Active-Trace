import { useQuery } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useAuditoriaMetricas() {
  return useQuery({
    queryKey: ['auditoria-metricas'],
    queryFn: () => adminService.getAuditoriaMetricas(),
  })
}
