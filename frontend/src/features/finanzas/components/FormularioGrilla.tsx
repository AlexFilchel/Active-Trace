import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { GrillaSalarial } from '../types'

const schema = z.object({
  categoria: z.string().min(1, 'La categoría es requerida'),
  salario_base: z.coerce.number().min(1, 'El salario base debe ser mayor a 0'),
})

type FormValues = z.infer<typeof schema>

interface Props {
  initial?: GrillaSalarial
  onSubmit: (data: FormValues) => void
  onCancel: () => void
  isLoading?: boolean
}

export function FormularioGrilla({ initial, onSubmit, onCancel, isLoading }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial
      ? { categoria: initial.categoria, salario_base: initial.salario_base }
      : { categoria: '', salario_base: 0 },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="grilla-categoria" className="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
        <input
          id="grilla-categoria"
          {...register('categoria')}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="ej. JTP, Titular, Ayudante"
        />
        {errors.categoria && (
          <p className="mt-1 text-xs text-red-600">{errors.categoria.message}</p>
        )}
      </div>
      <div>
        <label htmlFor="grilla-salario" className="block text-sm font-medium text-gray-700 mb-1">Salario Base ($)</label>
        <input
          id="grilla-salario"
          type="number"
          {...register('salario_base')}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.salario_base && (
          <p className="mt-1 text-xs text-red-600">{errors.salario_base.message}</p>
        )}
      </div>
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          {isLoading ? 'Guardando…' : 'Guardar'}
        </button>
      </div>
    </form>
  )
}
