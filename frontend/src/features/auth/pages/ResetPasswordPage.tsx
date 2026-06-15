import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authService } from '@/features/auth/services/authService'

const schema = z.object({
  newPassword: z
    .string()
    .min(8, 'La contraseña debe tener al menos 8 caracteres'),
})

type FormValues = z.infer<typeof schema>

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutateAsync, isPending, isError, error } = useMutation({
    mutationFn: ({ newPassword }: FormValues) => authService.resetPassword(token, newPassword),
    onSuccess: () => navigate('/login'),
  })

  const onSubmit = async (data: FormValues) => {
    try {
      await mutateAsync(data)
    } catch {
      // handled by react-query
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
          Restablecer contraseña
        </h1>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="newPassword"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Nueva contraseña
            </label>
            <input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              {...register('newPassword')}
            />
            {errors.newPassword && (
              <p className="mt-1 text-sm text-red-600">{errors.newPassword.message}</p>
            )}
          </div>

          {isError && (
            <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">
                {error instanceof Error
                  ? error.message
                  : 'El enlace es inválido o expiró. Solicitá uno nuevo.'}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full py-2 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {isPending ? 'Guardando…' : 'Restablecer contraseña'}
          </button>
        </form>
      </div>
    </div>
  )
}
