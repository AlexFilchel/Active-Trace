import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authService } from '@/features/auth/services/authService'
import {
  setAccessToken,
  setRefreshToken,
} from '@/features/auth/services/sessionStore'
import { notifySessionChange } from './useSession'

interface LoginVars {
  email: string
  password: string
  tenantSlug?: string
}

export function useLogin() {
  const [challengeToken, setChallengeToken] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: ({ email, password, tenantSlug }: LoginVars) =>
      authService.login(email, password, tenantSlug),
    onSuccess: (data) => {
      if ('requires_two_factor' in data && data.requires_two_factor) {
        setChallengeToken(data.challenge_token)
      } else if ('access_token' in data) {
        setAccessToken(data.access_token)
        setRefreshToken(data.refresh_token)
        notifySessionChange()
        setChallengeToken(null)
      }
    },
  })

  return {
    ...mutation,
    challengeToken,
  }
}
