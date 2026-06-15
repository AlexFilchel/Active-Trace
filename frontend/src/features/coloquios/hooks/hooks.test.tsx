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

// ── useColoquios ──────────────────────────────────────────────────────────────
describe('useColoquios', () => {
  it('fetches coloquios successfully', async () => {
    const data = [
      {
        id: 'col1',
        materia: 'Prog I',
        comision_id: 'c1',
        fecha_convocatoria: '2024-12-01',
        estado: 'abierto',
        creado_en: '2024-11-01',
      },
    ]
    server.use(http.get(`${BASE}/api/coloquios`, () => HttpResponse.json(data)))
    const { useColoquios } = await import('./useColoquios')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useColoquios(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty when no coloquios (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/coloquios`, () => HttpResponse.json([])))
    const { useColoquios } = await import('./useColoquios')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useColoquios(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useColoquioDias ───────────────────────────────────────────────────────────
describe('useColoquioDias', () => {
  it('fetches dias for selected coloquio', async () => {
    const dias = [
      { id: 'd1', coloquio_id: 'col1', fecha: '2024-12-20', cupo_maximo: 10, inscritos: 3 },
    ]
    server.use(
      http.get(`${BASE}/api/coloquios/:id/dias`, () => HttpResponse.json(dias)),
    )
    const { useColoquioDias } = await import('./useColoquioDias')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useColoquioDias('col1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(dias)
  })

  it('is idle when no coloquioId provided (triangulate)', async () => {
    const { useColoquioDias } = await import('./useColoquioDias')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useColoquioDias(undefined), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    expect(result.current.data).toBeUndefined()
  })
})
