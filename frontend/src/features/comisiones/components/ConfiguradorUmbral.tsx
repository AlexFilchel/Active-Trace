import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { UmbralConfig } from '../types'

const schema = z.object({
  umbral_pct: z
    .number({ invalid_type_error: 'Debe ser un número' })
    .min(0, 'Mínimo 0')
    .max(100, 'Máximo 100'),
})

type FormValues = z.infer<typeof schema>

interface Props {
  current?: UmbralConfig
  onSave: (umbralPct: number) => void
  isSaving?: boolean
}

export function ConfiguradorUmbral({ current, onSave, isSaving }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { umbral_pct: current?.umbral_pct ?? 60 },
  })

  function onSubmit(values: FormValues) {
    onSave(values.umbral_pct)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
      <div>
        <label htmlFor="umbral_pct" className="block text-sm font-medium text-gray-700">
          Umbral de aprobación (%)
        </label>
        <p className="text-sm text-gray-500">
          Umbral vigente: <span className="font-semibold">{current?.umbral_pct ?? 60}%</span>
        </p>
        <input
          id="umbral_pct"
          type="number"
          {...register('umbral_pct', { valueAsNumber: true })}
          className="mt-1 block w-32 rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
        {errors.umbral_pct && (
          <p className="mt-1 text-xs text-red-600">{errors.umbral_pct.message}</p>
        )}
      </div>
      <button
        type="submit"
        disabled={isSaving}
        className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isSaving ? 'Guardando…' : 'Guardar umbral'}
      </button>
    </form>
  )
}
