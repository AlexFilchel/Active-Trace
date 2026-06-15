import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '../services/adminService'
import type { UsuarioCreate } from '../types'

export function useCrearUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UsuarioCreate) => adminService.crearUsuario(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['usuarios'] }) },
  })
}
