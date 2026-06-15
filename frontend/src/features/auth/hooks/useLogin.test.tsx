import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { clearSession, getAccessToken } from '@/features/auth/services/sessionStore'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'

const BASE = 'http://localhost:8000'

function makeToken(): string {
  const payload = btoa(
    JSON.stringify({ sub: 'u1', tenant_id: 'ten-1', roles: ['ADMIN'], exp: 9999999999 }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

describe('useLogin', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('sets session on successful token response', async () => {
    const access = makeToken()
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({ access_token: access, refresh_token: 'rt-1', token_type: 'bearer' }),
      ),
    )

    const { useLogin } = await import('./useLogin')
    const { result } = renderHook(() => useLogin(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({ email: 'u@test.com', password: 'pass' })
    })

    expect(getAccessToken()).toBe(access)
    expect(result.current.challengeToken).toBeNull()
  })

  it('exposes challenge_token on requires_two_factor response (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({
          requires_two_factor: true,
          challenge_token: 'ch-123',
          expires_in: 300,
        }),
      ),
    )

    const { useLogin } = await import('./useLogin')
    const { result } = renderHook(() => useLogin(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({ email: 'u@test.com', password: 'pass' })
    })

    expect(getAccessToken()).toBeNull() // no session yet
    expect(result.current.challengeToken).toBe('ch-123')
  })

  it('exposes error on failed login (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 }),
      ),
    )

    const { useLogin } = await import('./useLogin')
    const { result } = renderHook(() => useLogin(), { wrapper })

    await act(async () => {
      try {
        await result.current.mutateAsync({ email: 'u@test.com', password: 'wrong' })
      } catch {
        // expected
      }
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(getAccessToken()).toBeNull()
  })
})
