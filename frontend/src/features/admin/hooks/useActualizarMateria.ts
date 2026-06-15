import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { MateriaCreate } from '../types'

export function useActualizarMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MateriaCreate> }) =>
      adminService.actualizarMateria(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['materias'] }) },
  })
}
