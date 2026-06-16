import { describe, it, expect, beforeEach } from 'vitest'
import {
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  getRefreshToken,
  setRefreshToken,
  clearRefreshToken,
  getClaims,
  isExpired,
  clearSession,
} from './sessionStore'

const VALID_JWT =
  // header.payload.sig — payload: { sub: 'user-1', tenant_id: 'ten-1', roles: ['ADMIN'], exp: 9999999999 }
  'eyJhbGciOiJIUzI1NiJ9.' +
  btoa(JSON.stringify({ sub: 'user-1', tenant_id: 'ten-1', roles: ['ADMIN'], exp: 9999999999 }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '') +
  '.signature'

const EXPIRED_JWT =
  'eyJhbGciOiJIUzI1NiJ9.' +
  btoa(JSON.stringify({ sub: 'user-2', tenant_id: 'ten-2', roles: ['ALUMNO'], exp: 1 }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '') +
  '.signature'

describe('sessionStore — access token (in-memory)', () => {
  beforeEach(() => clearSession())

  it('returns null when no token is set', () => {
    expect(getAccessToken()).toBeNull()
  })

  it('returns the token after set', () => {
    setAccessToken(VALID_JWT)
    expect(getAccessToken()).toBe(VALID_JWT)
  })

  it('returns null after clear', () => {
    setAccessToken(VALID_JWT)
    clearAccessToken()
    expect(getAccessToken()).toBeNull()
  })
})

describe('sessionStore — refresh token (localStorage)', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('returns null when no refresh token is stored', () => {
    expect(getRefreshToken()).toBeNull()
  })

  it('persists the refresh token in localStorage', () => {
    setRefreshToken('rt-abc')
    expect(getRefreshToken()).toBe('rt-abc')
    expect(localStorage.getItem('refresh_token')).toBe('rt-abc')
  })

  it('clears the refresh token from localStorage', () => {
    setRefreshToken('rt-abc')
    clearRefreshToken()
    expect(getRefreshToken()).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })
})

describe('sessionStore — JWT claims decoder', () => {
  beforeEach(() => clearSession())

  it('returns null when no access token is set', () => {
    expect(getClaims()).toBeNull()
  })

  it('decodes claims from a valid JWT', () => {
    setAccessToken(VALID_JWT)
    const claims = getClaims()
    expect(claims).not.toBeNull()
    expect(claims?.sub).toBe('user-1')
    expect(claims?.tenant_id).toBe('ten-1')
    expect(claims?.roles).toEqual(['ADMIN'])
    expect(claims?.exp).toBe(9999999999)
  })

  it('reports a future exp as NOT expired', () => {
    setAccessToken(VALID_JWT)
    expect(isExpired()).toBe(false)
  })

  it('reports a past exp as expired (triangulate)', () => {
    setAccessToken(EXPIRED_JWT)
    expect(isExpired()).toBe(true)
  })
})
