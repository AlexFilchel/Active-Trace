import { useMutation, useQueryClient } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

interface ActualizarUmbralVars {
  comisionId: ComisionId
  umbralPct: number
  valoresAprobatorios: number[]
}

export function useActualizarUmbral() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ comisionId, umbralPct, valoresAprobatorios }: ActualizarUmbralVars) =>
      comisionesService.putUmbral(comisionId, umbralPct, valoresAprobatorios),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ['comisiones', vars.comisionId, 'umbral'] })
    },
  })
}
