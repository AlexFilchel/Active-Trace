import { useMutation, useQueryClient } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

interface ImportarVars {
  comisionId: ComisionId
  file: File
  actividades: string[]
}

export function useImportarCalificaciones() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ comisionId, file, actividades }: ImportarVars) =>
      comisionesService.importarCalificaciones(comisionId, file, actividades),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ['comisiones', vars.comisionId] })
    },
  })
}
