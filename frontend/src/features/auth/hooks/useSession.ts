import { useState, useCallback, useEffect } from 'react'
import {
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  clearSession,
  getClaims,
  isExpired,
} from '@/features/auth/services/sessionStore'
import { authService } from '@/features/auth/services/authService'

function deriveSession() {
  const token = getAccessToken()
  if (!token || isExpired()) {
    return { isAuthenticated: false, userId: null, tenantId: null, roles: [] as string[] }
  }
  const claims = getClaims()
  if (!claims) {
    return { isAuthenticated: false, userId: null, tenantId: null, roles: [] as string[] }
  }
  return {
    isAuthenticated: true,
    userId: claims.sub,
    tenantId: claims.tenant_id,
    roles: claims.roles,
  }
}

// Singleton state so all useSession callers share the same value
let listeners: Array<() => void> = []

function notifyAll() {
  listeners.forEach((fn) => fn())
}

export function notifySessionChange() {
  notifyAll()
}

export function useSession() {
  const [session, setSession] = useState(deriveSession)

  useEffect(() => {
    const refresh = () => setSession(deriveSession())
    listeners.push(refresh)
    return () => {
      listeners = listeners.filter((l) => l !== refresh)
    }
  }, [])

  const logout = useCallback(async () => {
    const rt = getRefreshToken()
    try {
      if (rt) await authService.logout(rt)
    } catch {
      // ignore logout errors — always clear locally
    }
    clearSession()
    notifyAll()
  }, [])

  return { ...session, logout }
}

export function useRehydrateSession() {
  const [done, setDone] = useState(false)

  useEffect(() => {
    const rt = getRefreshToken()
    if (!rt) {
      setDone(true)
      return
    }
    // Access might be missing after reload — try refresh
    if (!getAccessToken()) {
      authService
        .refresh(rt)
        .then((res) => {
          setAccessToken(res.access_token)
          setRefreshToken(res.refresh_token)
          notifyAll()
        })
        .catch(() => {
          clearSession()
        })
        .finally(() => setDone(true))
    } else {
      setDone(true)
    }
  }, [])

  return { done }
}
