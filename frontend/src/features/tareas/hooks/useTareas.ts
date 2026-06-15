import { useQuery } from '@tanstack/react-query'
import { tareasService } from '../services/tareasService'

export function useTareas() {
  return useQuery({
    queryKey: ['tareas'],
    queryFn: () => tareasService.getTareas(),
  })
}
