import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import {
  clearSession,
  setAccessToken,
  setRefreshToken,
  getAccessToken,
  getRefreshToken,
} from '@/features/auth/services/sessionStore'

// We need to reset the api module between tests that change interceptor state
// Use dynamic import so we get a fresh module per test file execution

const BASE = 'http://localhost:8000'

// Helper to build a JWT-shaped token with future exp
function makeToken(sub = 'u1', roles = ['ADMIN'], exp = 9999999999): string {
  const payload = btoa(JSON.stringify({ sub, tenant_id: 'ten-1', roles, exp }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

const VALID_ACCESS = makeToken()
const NEW_ACCESS = makeToken('u1', ['ADMIN'], 9999999998)
const ROTATED_REFRESH = 'rotated-rt'

describe('api — request interceptor (bearer injection)', () => {
  beforeEach(() => {
    clearSession()
  })

  it('attaches Authorization header when access token is set', async () => {
    setAccessToken(VALID_ACCESS)
    let capturedAuth: string | null = null

    server.use(
      http.get(`${BASE}/api/protected`, ({ request }) => {
        capturedAuth = request.headers.get('authorization')
        return HttpResponse.json({ ok: true })
      }),
    )

    const { apiClient } = await import('./api')
    await apiClient.get('/api/protected')
    expect(capturedAuth).toBe(`Bearer ${VALID_ACCESS}`)
  })

  it('does NOT attach Authorization header when no session exists (triangulate)', async () => {
    // clearSession already called in beforeEach
    let capturedAuth: string | null = 'sentinel'

    server.use(
      http.get(`${BASE}/api/public-info`, ({ request }) => {
        capturedAuth = request.headers.get('authorization')
        return HttpResponse.json({ ok: true })
      }),
    )

    const { apiClient } = await import('./api')
    await apiClient.get('/api/public-info')
    expect(capturedAuth).toBeNull()
  })
})

describe('api — response interceptor (transparent refresh)', () => {
  beforeEach(() => {
    clearSession()
  })

  it('on 401: refreshes token and retries the original request', async () => {
    setRefreshToken('initial-rt')
    let refreshCalled = false
    let retryCount = 0

    server.use(
      http.get(`${BASE}/api/data`, () => {
        retryCount++
        if (retryCount === 1) {
          return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }
        return HttpResponse.json({ data: 'ok' })
      }),
      http.post(`${BASE}/api/auth/refresh`, () => {
        refreshCalled = true
        return HttpResponse.json({
          access_token: NEW_ACCESS,
          refresh_token: ROTATED_REFRESH,
          token_type: 'bearer',
        })
      }),
    )

    const { apiClient } = await import('./api')
    const res = await apiClient.get('/api/data')

    expect(refreshCalled).toBe(true)
    expect(retryCount).toBe(2)
    expect(res.data).toEqual({ data: 'ok' })
    expect(getAccessToken()).toBe(NEW_ACCESS)
    expect(getRefreshToken()).toBe(ROTATED_REFRESH)
  })

  it('does NOT retry or refresh on 403', async () => {
    setAccessToken(VALID_ACCESS)
    setRefreshToken('rt-1')
    let refreshCalled = false

    server.use(
      http.get(`${BASE}/api/admin-only`, () => {
        return HttpResponse.json({ error: 'Forbidden' }, { status: 403 })
      }),
      http.post(`${BASE}/api/auth/refresh`, () => {
        refreshCalled = true
        return HttpResponse.json({})
      }),
    )

    const { apiClient } = await import('./api')
    await expect(apiClient.get('/api/admin-only')).rejects.toThrow()
    expect(refreshCalled).toBe(false)
  })

  it('anti-loop: a request that already retried and gets 401 again clears the session', async () => {
    setRefreshToken('rt-loop')
    let refreshCallCount = 0

    server.use(
      http.get(`${BASE}/api/loop-test`, () => {
        return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
      }),
      http.post(`${BASE}/api/auth/refresh`, () => {
        refreshCallCount++
        return HttpResponse.json({
          access_token: NEW_ACCESS,
          refresh_token: ROTATED_REFRESH,
          token_type: 'bearer',
        })
      }),
    )

    const { apiClient } = await import('./api')
    await expect(apiClient.get('/api/loop-test')).rejects.toThrow()
    expect(refreshCallCount).toBe(1) // only one refresh attempted
    expect(getAccessToken()).toBeNull() // session cleared
  })

  it('refresh failure clears session', async () => {
    setRefreshToken('invalid-rt')

    server.use(
      http.get(`${BASE}/api/data2`, () => {
        return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
      }),
      http.post(`${BASE}/api/auth/refresh`, () => {
        return HttpResponse.json({ error: 'Invalid' }, { status: 401 })
      }),
    )

    const { apiClient } = await import('./api')
    await expect(apiClient.get('/api/data2')).rejects.toThrow()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })
})

describe('api — concurrent 401 deduplication (mutex)', () => {
  beforeEach(() => {
    clearSession()
  })

  it('N concurrent 401s trigger exactly ONE refresh call', async () => {
    setRefreshToken('shared-rt')
    let refreshCallCount = 0
    let requestCallCount = 0

    server.use(
      http.get(`${BASE}/api/concurrent`, () => {
        requestCallCount++
        if (requestCallCount <= 3) {
          return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }
        return HttpResponse.json({ data: 'ok' })
      }),
      http.post(`${BASE}/api/auth/refresh`, async () => {
        refreshCallCount++
        // Simulate async work
        await new Promise((r) => setTimeout(r, 10))
        return HttpResponse.json({
          access_token: NEW_ACCESS,
          refresh_token: ROTATED_REFRESH,
          token_type: 'bearer',
        })
      }),
    )

    const { apiClient } = await import('./api')
    // Fire 3 concurrent requests that all will get 401
    const results = await Promise.allSettled([
      apiClient.get('/api/concurrent'),
      apiClient.get('/api/concurrent'),
      apiClient.get('/api/concurrent'),
    ])

    expect(refreshCallCount).toBe(1) // only one refresh issued
    const fulfilled = results.filter((r) => r.status === 'fulfilled')
    expect(fulfilled.length).toBeGreaterThan(0) // at least one succeeded
  })
})
