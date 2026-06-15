import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { createAppRouter } from '@/router/index'
import { clearSession, setAccessToken, setRefreshToken } from '@/features/auth/services/sessionStore'
import React from 'react'

const BASE = 'http://localhost:8000'

function makeToken(roles = ['PROFESOR']): string {
  const payload = btoa(JSON.stringify({ sub: 'u1', tenant_id: 'ten-1', roles, exp: 9999999999 }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

// ── 8.2 /comisiones route ─────────────────────────────────────────────────────
describe('Router — /comisiones route', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
    server.use(
      http.get(`${BASE}/api/calificaciones/actividades`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/calificaciones/umbral`, () => HttpResponse.json(null, { status: 404 })),
      http.get(`${BASE}/api/atrasados`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/analisis/ranking`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/calificaciones/notas-finales`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/analisis/reporte-rapido`, () => HttpResponse.json({ total_alumnos: 0, aprobados: 0, reprobados: 0, sin_nota: 0, atrasados: 0, promedio_general: null })),
      http.get(`${BASE}/api/analisis/entregas-sin-corregir`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/comunicaciones/estado`, () => HttpResponse.json([])),
    )
  })

  it('/comisiones renders ComisionesPage for authenticated PROFESOR', async () => {
    setAccessToken(makeToken(['PROFESOR']))
    setRefreshToken('rt-1')
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createAppRouter({ initialPath: '/comisiones' })
    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(RouterProvider, { router }),
      ),
    )
    expect(await screen.findByText(/Comisiones/i)).toBeInTheDocument()
  })

  it('/comisiones redirects to /login when unauthenticated (triangulate)', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createAppRouter({ initialPath: '/comisiones' })
    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(RouterProvider, { router }),
      ),
    )
    expect(await screen.findByRole('button', { name: /ingresar|login|entrar/i })).toBeInTheDocument()
  })
})

// ── 8.3 PROFESOR sees Comisiones nav ──────────────────────────────────────────
describe('AuthenticatedLayout — PROFESOR nav visibility', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('PROFESOR sees Comisiones nav link', async () => {
    setAccessToken(makeToken(['PROFESOR']))
    setRefreshToken('rt-1')
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createAppRouter({ initialPath: '/dashboard' })
    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(RouterProvider, { router }),
      ),
    )
    expect(await screen.findByRole('link', { name: /^Comisiones$/i })).toBeInTheDocument()
  })

  it('ALUMNO does not see Comisiones nav link (triangulate)', async () => {
    setAccessToken(makeToken(['ALUMNO']))
    setRefreshToken('rt-1')
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createAppRouter({ initialPath: '/dashboard' })
    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(RouterProvider, { router }),
      ),
    )
    // wait for render to settle
    expect(await screen.findByRole('button', { name: /cerrar sesión/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^Comisiones$/i })).not.toBeInTheDocument()
  })
})
