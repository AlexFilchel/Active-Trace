import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import {
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  clearSession,
} from '@/features/auth/services/sessionStore'
import type { RefreshResponse } from '@/features/auth/types'

// Extend AxiosRequestConfig to carry our retry flag
interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

// Mutex — ensure only one refresh in flight at a time
let refreshPromise: Promise<string> | null = null

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── REQUEST: inject Bearer token ────────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── RESPONSE: transparent refresh on 401, propagate 403 ────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableConfig | undefined

    if (!originalRequest) {
      return Promise.reject(error)
    }

    // 403 → propagate immediately, no refresh
    if (error.response?.status === 403) {
      return Promise.reject(error)
    }

    // 401 handling
    if (error.response?.status === 401) {
      // Anti-loop: if this request already retried once, clear session and bail
      if (originalRequest._retry) {
        clearSession()
        return Promise.reject(error)
      }

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearSession()
        return Promise.reject(error)
      }

      originalRequest._retry = true

      // Single-flight mutex: if a refresh is already in progress, await it
      if (!refreshPromise) {
        refreshPromise = axios
          .post<RefreshResponse>('http://localhost:8000/api/auth/refresh', {
            refresh_token: refreshToken,
          })
          .then((res) => {
            setAccessToken(res.data.access_token)
            setRefreshToken(res.data.refresh_token)
            return res.data.access_token
          })
          .catch((refreshError: unknown) => {
            clearSession()
            throw refreshError
          })
          .finally(() => {
            refreshPromise = null
          })
      }

      try {
        const newAccessToken = await refreshPromise
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      } catch {
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)
