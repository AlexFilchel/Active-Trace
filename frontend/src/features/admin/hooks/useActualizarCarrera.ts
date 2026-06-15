import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { CarreraCreate } from '../types'

export function useActualizarCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CarreraCreate> }) =>
      adminService.actualizarCarrera(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['carreras'] }) },
  })
}
