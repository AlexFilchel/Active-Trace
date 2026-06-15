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
  }
}

// ── useEncuentros ─────────────────────────────────────────────────────────────
describe('useEncuentros', () => {
  it('fetches encuentros successfully', async () => {
    const data = [
      {
        id: 'en1',
        titulo: 'Clase 1',
        fecha: '2024-08-01',
        hora_inicio: '18:00',
        hora_fin: '20:00',
        comision_id: 'c1',
        tipo: 'clase',
      },
    ]
    server.use(http.get(`${BASE}/api/encuentros`, () => HttpResponse.json(data)))
    const { useEncuentros } = await import('./useEncuentros')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEncuentros(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no encuentros (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/encuentros`, () => HttpResponse.json([])))
    const { useEncuentros } = await import('./useEncuentros')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEncuentros(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useGuardias ───────────────────────────────────────────────────────────────
describe('useGuardias', () => {
  it('fetches guardias successfully', async () => {
    const data = [
      {
        id: 'g1',
        tutor_id: 'u1',
        tutor_nombre: 'Ana López',
        fecha: '2024-08-01',
        hora_inicio: '14:00',
        hora_fin: '16:00',
      },
    ]
    server.use(http.get(`${BASE}/api/guardias`, () => HttpResponse.json(data)))
    const { useGuardias } = await import('./useGuardias')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useGuardias(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty when no guardias (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/guardias`, () => HttpResponse.json([])))
    const { useGuardias } = await import('./useGuardias')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useGuardias(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})
