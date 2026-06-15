import { useQuery } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useCohortes() {
  return useQuery({
    queryKey: ['cohortes'],
    queryFn: () => adminService.getCohortes(),
  })
}
