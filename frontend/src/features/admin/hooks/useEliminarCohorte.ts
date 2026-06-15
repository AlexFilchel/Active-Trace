import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useEliminarCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminService.eliminarCohorte(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cohortes'] }) },
  })
}
