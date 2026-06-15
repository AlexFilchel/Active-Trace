import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { RolUsuario } from '../types'

export function useAsignarRoles() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, roles }: { id: string; roles: RolUsuario[] }) =>
      adminService.asignarRoles(id, roles),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['usuarios'] }) },
  })
}
