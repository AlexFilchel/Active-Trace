import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  proveedor: z.string().min(1, 'El proveedor es requerido'),
  monto: z.coerce.number().min(0.01, 'El monto debe ser mayor a 0'),
  descripcion: z.string().min(1, 'La descripción es requerida'),
})

type FormValues = z.infer<typeof schema>

interface FacturaInitial {
  proveedor?: string
  monto?: number
  descripcion?: string
}

interface Props {
  initial?: FacturaInitial
  onSubmit: (data: FormValues) => void
  onCancel: () => void
  isLoading?: boolean
}

export function FormularioFactura({ initial, onSubmit, onCancel, isLoading }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      proveedor: initial?.proveedor ?? '',
      monto: initial?.monto ?? 0,
      descripcion: initial?.descripcion ?? '',
    },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="factura-proveedor" className="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
        <input
          id="factura-proveedor"
          {...register('proveedor')}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.proveedor && (
          <p className="mt-1 text-xs text-red-600">{errors.proveedor.message}</p>
        )}
      </div>
      <div>
        <label htmlFor="factura-monto" className="block text-sm font-medium text-gray-700 mb-1">Monto ($)</label>
        <input
          id="factura-monto"
          type="number"
          step="0.01"
          {...register('monto')}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.monto && (
          <p className="mt-1 text-xs text-red-600">{errors.monto.message}</p>
        )}
      </div>
      <div>
        <label htmlFor="factura-descripcion" className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
        <textarea
          id="factura-descripcion"
          {...register('descripcion')}
          rows={3}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.descripcion && (
          <p className="mt-1 text-xs text-red-600">{errors.descripcion.message}</p>
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
          {isLoading ? 'Guardando…' : 'Registrar factura'}
        </button>
      </div>
    </form>
  )
}
