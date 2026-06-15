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

// ── useAvisos ─────────────────────────────────────────────────────────────────
describe('useAvisos', () => {
  it('fetches avisos successfully', async () => {
    const data = [
      {
        id: 'av1',
        titulo: 'Test',
        cuerpo: 'cuerpo',
        scope: 'tenant',
        publicado: true,
        creado_en: '2024-01-01',
      },
    ]
    server.use(http.get(`${BASE}/api/avisos`, () => HttpResponse.json(data)))
    const { useAvisos } = await import('./useAvisos')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAvisos(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no avisos (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/avisos`, () => HttpResponse.json([])))
    const { useAvisos } = await import('./useAvisos')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAvisos(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useCreateAviso ────────────────────────────────────────────────────────────
describe('useCreateAviso', () => {
  it('creates aviso and returns created aviso', async () => {
    const created = {
      id: 'av2',
      titulo: 'Nuevo',
      cuerpo: 'cuerpo',
      scope: 'tenant',
      publicado: false,
      creado_en: '2024-06-01',
    }
    server.use(
      http.get(`${BASE}/api/avisos`, () => HttpResponse.json([])),
      http.post(`${BASE}/api/avisos`, () => HttpResponse.json(created, { status: 201 })),
    )
    const { useCreateAviso } = await import('./useCreateAviso')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCreateAviso(), { wrapper })
    result.current.mutate({ titulo: 'Nuevo', cuerpo: 'cuerpo', scope: 'tenant' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(created)
  })

  it('is in error state on validation failure (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/avisos`, () =>
        HttpResponse.json({ detail: 'Error' }, { status: 422 }),
      ),
    )
    const { useCreateAviso } = await import('./useCreateAviso')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCreateAviso(), { wrapper })
    result.current.mutate({ titulo: '', cuerpo: '', scope: 'tenant' })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
