import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import {
  clearSession,
  setAccessToken,
  setRefreshToken,
} from '@/features/auth/services/sessionStore'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'

const BASE = 'http://localhost:8000'

function makeToken(sub = 'u1', roles = ['ADMIN'], exp = 9999999999): string {
  const payload = btoa(JSON.stringify({ sub, tenant_id: 'ten-1', roles, exp }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

describe('useSession', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('isAuthenticated is false when no session exists', async () => {
    const { useSession } = await import('./useSession')
    const { result } = renderHook(() => useSession(), { wrapper })
    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(false)
    })
    expect(result.current.userId).toBeNull()
    expect(result.current.roles).toEqual([])
  })

  it('exposes identity from JWT claims when session is active', async () => {
    const token = makeToken('user-42', ['COORDINADOR'])
    setAccessToken(token)

    const { useSession } = await import('./useSession')
    const { result } = renderHook(() => useSession(), { wrapper })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })
    expect(result.current.userId).toBe('user-42')
    expect(result.current.tenantId).toBe('ten-1')
    expect(result.current.roles).toEqual(['COORDINADOR'])
  })

  it('logout clears session (triangulate)', async () => {
    const token = makeToken()
    setAccessToken(token)
    setRefreshToken('rt-logout')

    server.use(
      http.post(`${BASE}/api/auth/logout`, () => new HttpResponse(null, { status: 204 })),
    )

    const { useSession } = await import('./useSession')
    const { result } = renderHook(() => useSession(), { wrapper })

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true))

    await act(async () => {
      await result.current.logout()
    })

    expect(result.current.isAuthenticated).toBe(false)
  })
})

describe('useSession — rehydration on boot', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('restores session from stored refresh token', async () => {
    localStorage.setItem('refresh_token', 'stored-rt')
    const newAccess = makeToken('rehydrated-user')

    server.use(
      http.post(`${BASE}/api/auth/refresh`, () =>
        HttpResponse.json({
          access_token: newAccess,
          refresh_token: 'new-rt',
          token_type: 'bearer',
        }),
      ),
    )

    const { useRehydrateSession } = await import('./useSession')
    const { result } = renderHook(() => useRehydrateSession(), { wrapper })

    await waitFor(() => {
      expect(result.current.done).toBe(true)
    })

    const { useSession } = await import('./useSession')
    const { result: sessionResult } = renderHook(() => useSession(), { wrapper })
    await waitFor(() => {
      expect(sessionResult.current.isAuthenticated).toBe(true)
    })
  })

  it('no session when no refresh token stored (triangulate)', async () => {
    // No localStorage entry
    const { useRehydrateSession } = await import('./useSession')
    const { result } = renderHook(() => useRehydrateSession(), { wrapper })

    await waitFor(() => {
      expect(result.current.done).toBe(true)
    })

    const { useSession } = await import('./useSession')
    const { result: sessionResult } = renderHook(() => useSession(), { wrapper })
    await waitFor(() => {
      expect(sessionResult.current.isAuthenticated).toBe(false)
    })
  })
})
