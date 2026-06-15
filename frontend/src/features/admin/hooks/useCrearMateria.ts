import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { MateriaCreate } from '../types'

export function useCrearMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: MateriaCreate) => adminService.crearMateria(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['materias'] }) },
  })
}
