import { useMutation } from '@tanstack/react-query'
import { comisionesService } from '../services/comisionesService'
import type { ComisionId } from '../types'

interface PreviewVars {
  comisionId: ComisionId
  tipo: string
}

export function usePreviewComunicacion() {
  return useMutation({
    mutationFn: ({ comisionId, tipo }: PreviewVars) =>
      comisionesService.previewComunicacion(comisionId, tipo),
  })
}
