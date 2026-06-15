import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { CohorteCreate } from '../types'

export function useActualizarCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CohorteCreate> }) =>
      adminService.actualizarCohorte(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cohortes'] }) },
  })
}
