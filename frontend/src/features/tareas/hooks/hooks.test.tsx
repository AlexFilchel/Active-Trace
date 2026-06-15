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

// ── useTareas ─────────────────────────────────────────────────────────────────
describe('useTareas', () => {
  it('fetches tareas successfully', async () => {
    const data = [
      { id: 't1', titulo: 'Tarea 1', estado: 'pendiente', prioridad: 'alta', creado_en: '2024-01-01' },
    ]
    server.use(http.get(`${BASE}/api/tareas`, () => HttpResponse.json(data)))
    const { useTareas } = await import('./useTareas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useTareas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no tareas (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/tareas`, () => HttpResponse.json([])))
    const { useTareas } = await import('./useTareas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useTareas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useUpdateTarea ────────────────────────────────────────────────────────────
describe('useUpdateTarea', () => {
  it('transitions tarea estado via PUT (workflow happy path)', async () => {
    const updated = { id: 't1', titulo: 'T1', estado: 'en_progreso', prioridad: 'alta', creado_en: '2024-01-01' }
    server.use(
      http.get(`${BASE}/api/tareas`, () => HttpResponse.json([])),
      http.put(`${BASE}/api/tareas/:id`, () => HttpResponse.json(updated)),
    )
    const { useUpdateTarea } = await import('./useUpdateTarea')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUpdateTarea(), { wrapper })
    result.current.mutate({ id: 't1', data: { estado: 'en_progreso' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.estado).toBe('en_progreso')
  })

  it('transitions to completada (triangulate)', async () => {
    const updated = { id: 't1', titulo: 'T1', estado: 'completada', prioridad: 'alta', creado_en: '2024-01-01' }
    server.use(
      http.get(`${BASE}/api/tareas`, () => HttpResponse.json([])),
      http.put(`${BASE}/api/tareas/:id`, () => HttpResponse.json(updated)),
    )
    const { useUpdateTarea } = await import('./useUpdateTarea')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUpdateTarea(), { wrapper })
    result.current.mutate({ id: 't1', data: { estado: 'completada' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.estado).toBe('completada')
  })
})
