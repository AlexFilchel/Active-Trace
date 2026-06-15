import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authService } from '@/features/auth/services/authService'
import { setAccessToken, setRefreshToken } from '@/features/auth/services/sessionStore'
import { notifySessionChange } from '@/features/auth/hooks/useSession'

const schema = z.object({
  code: z.string().length(6, 'El código debe tener 6 dígitos'),
})

type FormValues = z.infer<typeof schema>

interface LocationState {
  challengeToken?: string
}

export default function TwoFactorPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state ?? {}) as LocationState
  const challengeToken = state.challengeToken ?? ''

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutateAsync, isPending, isError, error } = useMutation({
    mutationFn: ({ code }: FormValues) => authService.verifyLogin2fa(challengeToken, code),
    onSuccess: (data) => {
      setAccessToken(data.access_token)
      setRefreshToken(data.refresh_token)
      notifySessionChange()
    },
  })

  const onSubmit = async (data: FormValues) => {
    try {
      await mutateAsync(data)
      navigate('/dashboard')
    } catch {
      // handled by react-query
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-semibold text-gray-800 mb-2 text-center">
          Verificación en dos pasos
        </h1>
        <p className="text-sm text-gray-600 text-center mb-6">
          Ingresá el código de tu aplicación de autenticación.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div>
            <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
              Código
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              autoComplete="one-time-code"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-center text-2xl tracking-widest focus:outline-none focus:ring-2 focus:ring-indigo-500"
              {...register('code')}
            />
            {errors.code && (
              <p className="mt-1 text-sm text-red-600">{errors.code.message}</p>
            )}
          </div>

          {isError && (
            <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">
                {error instanceof Error ? error.message : 'Código inválido. Intentá de nuevo.'}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full py-2 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {isPending ? 'Verificando…' : 'Verificar'}
          </button>
        </form>
      </div>
    </div>
  )
}
