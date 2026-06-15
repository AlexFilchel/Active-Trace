import { useMutation, useQueryClient } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

interface EnviarVars {
  comisionId: ComisionId
  tipo: string
  mensajePersonalizado?: string
}

export function useEnviarComunicacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ comisionId, tipo, mensajePersonalizado }: EnviarVars) =>
      comisionesService.enviarComunicacion(comisionId, tipo, mensajePersonalizado),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({
        queryKey: ['comisiones', vars.comisionId, 'comunicaciones-estado'],
      })
    },
  })
}
