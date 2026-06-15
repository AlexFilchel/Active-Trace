import { useMutation, useQueryClient } from '@tanstack/react-query'
import { coloquiosService } from '../services/coloquiosService'
import type { ColoquioCreate } from '../types'

export function useCreateColoquio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ColoquioCreate) => coloquiosService.createColoquio(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['coloquios'] }),
  })
}
