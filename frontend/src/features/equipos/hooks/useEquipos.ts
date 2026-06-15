import { useQuery } from '@tanstack/react-query'
import { equiposService } from '../services/equiposService'

export function useEquipos() {
  return useQuery({
    queryKey: ['equipos'],
    queryFn: () => equiposService.getEquipos(),
  })
}
