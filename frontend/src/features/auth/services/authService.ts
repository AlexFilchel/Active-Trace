import { apiClient } from '@/shared/services/api'
import type { LoginResponse, LoginTokenResponse, RefreshResponse } from '../types'

export const authService = {
  async login(email: string, password: string, tenantSlug?: string): Promise<LoginResponse> {
    const res = await apiClient.post<LoginResponse>('/api/auth/login', {
      email,
      password,
      ...(tenantSlug ? { tenant_slug: tenantSlug } : {}),
    })
    return res.data
  },

  async verifyLogin2fa(challengeToken: string, code: string): Promise<LoginTokenResponse> {
    const res = await apiClient.post<LoginTokenResponse>('/api/auth/2fa/verify-login', {
      challenge_token: challengeToken,
      code,
    })
    return res.data
  },

  async forgotPassword(email: string): Promise<void> {
    await apiClient.post('/api/auth/forgot', { email })
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiClient.post('/api/auth/reset', { token, new_password: newPassword })
  },

  async logout(refreshToken: string): Promise<void> {
    await apiClient.post('/api/auth/logout', { refresh_token: refreshToken })
  },

  async refresh(refreshToken: string): Promise<RefreshResponse> {
    const res = await apiClient.post<RefreshResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    })
    return res.data
  },
}
