import { useQuery } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { AuditoriaFiltros } from '../types'

export function useAuditoriaLog(filtros: AuditoriaFiltros, page: number, pageSize = 20) {
  return useQuery({
    queryKey: ['auditoria-log', filtros, page, pageSize],
    queryFn: () => adminService.getAuditoriaLog(filtros, page, pageSize),
  })
}
