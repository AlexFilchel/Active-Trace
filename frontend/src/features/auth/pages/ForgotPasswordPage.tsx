import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authService } from '@/features/auth/services/authService'

const schema = z.object({
  email: z.string().email('Email inválido'),
})

type FormValues = z.infer<typeof schema>

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutateAsync, isPending } = useMutation({
    mutationFn: ({ email }: FormValues) => authService.forgotPassword(email),
    onSuccess: () => setSent(true),
    onError: () => setSent(true), // always show neutral confirmation
  })

  const onSubmit = async (data: FormValues) => {
    await mutateAsync(data)
  }

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-full max-w-md p-8 bg-white rounded-lg shadow text-center">
          <h1 className="text-2xl font-semibold text-gray-800 mb-4">Revisá tu email</h1>
          <p className="text-gray-600">
            Si existe una cuenta con ese email, te enviamos un enlace para restablecer tu contraseña.
          </p>
          <a href="/login" className="mt-6 inline-block text-indigo-600 hover:underline text-sm">
            Volver al inicio de sesión
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-semibold text-gray-800 mb-2 text-center">
          Recuperar contraseña
        </h1>
        <p className="text-sm text-gray-600 text-center mb-6">
          Ingresá tu email y te enviamos un enlace para restablecer tu contraseña.
        </p>

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

          <button
            type="submit"
            disabled={isPending}
            className="w-full py-2 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {isPending ? 'Enviando…' : 'Enviar enlace'}
          </button>
        </form>
      </div>
    </div>
  )
}
