import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useLogin } from '@/features/auth/hooks/useLogin'
import { useEffect } from 'react'

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña requerida'),
  tenantSlug: z.string().optional(),
})

type LoginFormValues = z.infer<typeof loginSchema>

export default function LoginPage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending, isError, error, challengeToken } = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  })

  useEffect(() => {
    if (challengeToken) {
      navigate('/2fa', { state: { challengeToken } })
    }
  }, [challengeToken, navigate])

  const onSubmit = async (data: LoginFormValues) => {
    try {
      await mutateAsync({ email: data.email, password: data.password, tenantSlug: data.tenantSlug })
      navigate('/dashboard')
    } catch {
      // error is handled by react-query state
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-semibold text-gray-800 mb-6 text-center">Ingresar</h1>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              {...register('email')}
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              {...register('password')}
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          {isError && (
            <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">
                {error instanceof Error ? error.message : 'Credenciales incorrectas. Intentá de nuevo.'}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full py-2 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {isPending ? 'Ingresando…' : 'Ingresar'}
          </button>

          <div className="text-center">
            <a href="/forgot" className="text-sm text-indigo-600 hover:underline">
              ¿Olvidaste tu contraseña?
            </a>
          </div>
        </form>
      </div>
    </div>
  )
}
