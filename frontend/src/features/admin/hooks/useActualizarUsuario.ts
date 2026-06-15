import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { UsuarioUpdate } from '../types'

export function useActualizarUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UsuarioUpdate }) =>
      adminService.actualizarUsuario(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['usuarios'] }) },
  })
}
