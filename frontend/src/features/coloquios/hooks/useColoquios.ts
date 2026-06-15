import { useQuery } from '@tanstack/react-query'
import { coloquiosService } from '../services/coloquiosService'

export function useColoquios() {
  return useQuery({
    queryKey: ['coloquios'],
    queryFn: () => coloquiosService.getColoquios(),
  })
}
