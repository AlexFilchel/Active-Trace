import { useQuery } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useMaterias() {
  return useQuery({
    queryKey: ['materias'],
    queryFn: () => adminService.getMaterias(),
  })
}
