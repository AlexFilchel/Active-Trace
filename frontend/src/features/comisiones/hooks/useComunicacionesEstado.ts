import { useQuery } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

export function useComunicacionesEstado(comisionId: ComisionId | undefined) {
  return useQuery({
    queryKey: ['comisiones', comisionId, 'comunicaciones-estado'],
    queryFn: () => comisionesService.getEstadoComunicaciones(comisionId!),
    enabled: !!comisionId,
    refetchInterval: 3000,
  })
}
