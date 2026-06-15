import type { JwtClaims } from '../types'

const REFRESH_TOKEN_KEY = 'refresh_token'

// Access token lives ONLY in memory — never persisted
let _accessToken: string | null = null

export function getAccessToken(): string | null {
  return _accessToken
}

export function setAccessToken(token: string): void {
  _accessToken = token
}

export function clearAccessToken(): void {
  _accessToken = null
}

// Refresh token persisted in localStorage so it survives page reloads
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export function clearRefreshToken(): void {
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function clearSession(): void {
  clearAccessToken()
  clearRefreshToken()
}

// Decode JWT payload (base64url) — client does NOT verify signature
function decodePayload(token: string): JwtClaims | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const payload = parts[1]
    // base64url → base64 → JSON
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const decoded = atob(padded)
    return JSON.parse(decoded) as JwtClaims
  } catch {
    return null
  }
}

export function getClaims(): JwtClaims | null {
  if (!_accessToken) return null
  return decodePayload(_accessToken)
}

export function isExpired(): boolean {
  const claims = getClaims()
  if (!claims) return true
  // exp is Unix timestamp in seconds
  return Date.now() / 1000 >= claims.exp
}
