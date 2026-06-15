import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import React from 'react'

const BASE = 'http://localhost:8000'

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return {
    wrapper: ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: qc }, children),
    qc,
  }
}

// ── useEquipos ────────────────────────────────────────────────────────────────
describe('useEquipos', () => {
  it('fetches equipos successfully', async () => {
    const data = [{ id: 'e1', nombre: 'Equipo A', vigente: true, creado_en: '2024-01-01' }]
    server.use(http.get(`${BASE}/api/equipos`, () => HttpResponse.json(data)))
    const { useEquipos } = await import('./useEquipos')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEquipos(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no equipos (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/equipos`, () => HttpResponse.json([])))
    const { useEquipos } = await import('./useEquipos')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEquipos(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useCreateEquipo ───────────────────────────────────────────────────────────
describe('useCreateEquipo', () => {
  it('calls POST /api/equipos and returns created equipo', async () => {
    const created = { id: 'e2', nombre: 'Nuevo', vigente: true, creado_en: '2024-06-01' }
    server.use(
      http.get(`${BASE}/api/equipos`, () => HttpResponse.json([])),
      http.post(`${BASE}/api/equipos`, () => HttpResponse.json(created, { status: 201 })),
    )
    const { useCreateEquipo } = await import('./useCreateEquipo')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCreateEquipo(), { wrapper })
    result.current.mutate({ nombre: 'Nuevo' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(created)
  })

  it('is in error state on server failure (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/equipos`, () =>
        HttpResponse.json({ detail: 'Error' }, { status: 500 }),
      ),
    )
    const { useCreateEquipo } = await import('./useCreateEquipo')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCreateEquipo(), { wrapper })
    result.current.mutate({ nombre: 'x' })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
