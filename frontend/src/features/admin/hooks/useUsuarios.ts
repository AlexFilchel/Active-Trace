import { useQuery } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useUsuarios() {
  return useQuery({
    queryKey: ['usuarios'],
    queryFn: () => adminService.getUsuarios(),
  })
}
