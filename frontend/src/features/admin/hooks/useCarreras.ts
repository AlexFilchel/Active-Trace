import { useQuery } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useCarreras() {
  return useQuery({
    queryKey: ['carreras'],
    queryFn: () => adminService.getCarreras(),
  })
}
