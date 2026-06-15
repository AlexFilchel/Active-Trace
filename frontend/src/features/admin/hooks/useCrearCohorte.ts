import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { CohorteCreate } from '../types'

export function useCrearCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CohorteCreate) => adminService.crearCohorte(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cohortes'] }) },
  })
}
