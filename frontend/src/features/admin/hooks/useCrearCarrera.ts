import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { CarreraCreate } from '../types'

export function useCrearCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CarreraCreate) => adminService.crearCarrera(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['carreras'] }) },
  })
}
