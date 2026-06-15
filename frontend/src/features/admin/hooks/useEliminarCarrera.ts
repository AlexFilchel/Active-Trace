import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'

export function useEliminarCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminService.eliminarCarrera(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['carreras'] }) },
  })
}
