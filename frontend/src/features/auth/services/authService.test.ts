import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { clearSession } from './sessionStore'

const BASE = 'http://localhost:8000'

function makeToken(sub = 'u1'): string {
  const payload = btoa(
    JSON.stringify({ sub, tenant_id: 'ten-1', roles: ['ADMIN'], exp: 9999999999 }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

describe('authService.login', () => {
  beforeEach(() => clearSession())

  it('returns token response on successful login', async () => {
    const tokenRes = {
      access_token: makeToken(),
      refresh_token: 'rt-1',
      token_type: 'bearer',
    }
    server.use(
      http.post(`${BASE}/api/auth/login`, () => HttpResponse.json(tokenRes)),
    )
    const { authService } = await import('./authService')
    const result = await authService.login('user@test.com', 'pass123')
    expect(result).toEqual(tokenRes)
  })

  it('returns requires_two_factor response when 2FA is needed (triangulate)', async () => {
    const tfaRes = {
      requires_two_factor: true,
      challenge_token: 'ch-tok-123',
      expires_in: 300,
    }
    server.use(
      http.post(`${BASE}/api/auth/login`, () => HttpResponse.json(tfaRes)),
    )
    const { authService } = await import('./authService')
    const result = await authService.login('user@test.com', 'pass123')
    expect(result).toEqual(tfaRes)
  })
})

describe('authService.verifyLogin2fa', () => {
  beforeEach(() => clearSession())

  it('returns tokens on valid code', async () => {
    const tokenRes = {
      access_token: makeToken(),
      refresh_token: 'rt-2',
      token_type: 'bearer',
    }
    server.use(
      http.post(`${BASE}/api/auth/2fa/verify-login`, () => HttpResponse.json(tokenRes)),
    )
    const { authService } = await import('./authService')
    const result = await authService.verifyLogin2fa('ch-tok', '123456')
    expect(result).toEqual(tokenRes)
  })

  it('throws on invalid code (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/2fa/verify-login`, () =>
        HttpResponse.json({ detail: 'Invalid code' }, { status: 400 }),
      ),
    )
    const { authService } = await import('./authService')
    await expect(authService.verifyLogin2fa('ch-tok', 'wrong')).rejects.toThrow()
  })
})

describe('authService.forgotPassword', () => {
  beforeEach(() => clearSession())

  it('resolves with neutral confirmation', async () => {
    server.use(
      http.post(`${BASE}/api/auth/forgot`, () =>
        new HttpResponse(null, { status: 202 }),
      ),
    )
    const { authService } = await import('./authService')
    await expect(authService.forgotPassword('any@example.com')).resolves.toBeUndefined()
  })
})

describe('authService.resetPassword', () => {
  beforeEach(() => clearSession())

  it('resolves on valid token', async () => {
    server.use(
      http.post(`${BASE}/api/auth/reset`, () => HttpResponse.json({ ok: true })),
    )
    const { authService } = await import('./authService')
    await expect(authService.resetPassword('valid-tok', 'newPass1!')).resolves.toBeUndefined()
  })

  it('throws on invalid token (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/reset`, () =>
        HttpResponse.json({ detail: 'Invalid token' }, { status: 400 }),
      ),
    )
    const { authService } = await import('./authService')
    await expect(authService.resetPassword('bad-tok', 'newPass1!')).rejects.toThrow()
  })
})

describe('authService.logout', () => {
  beforeEach(() => clearSession())

  it('resolves on 204', async () => {
    server.use(
      http.post(`${BASE}/api/auth/logout`, () => new HttpResponse(null, { status: 204 })),
    )
    const { authService } = await import('./authService')
    await expect(authService.logout('rt-99')).resolves.toBeUndefined()
  })
})
