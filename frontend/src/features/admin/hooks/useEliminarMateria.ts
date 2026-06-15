import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useEliminarMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminService.eliminarMateria(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['materias'] }) },
  })
}
