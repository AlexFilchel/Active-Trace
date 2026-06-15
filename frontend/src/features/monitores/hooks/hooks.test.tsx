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

// ── useMonitorGeneral ─────────────────────────────────────────────────────────
describe('useMonitorGeneral', () => {
  it('fetches monitor general items', async () => {
    const data = [
      {
        alumno_id: 'u1',
        nombre: 'Juan',
        apellido: 'Pérez',
        legajo: '12345',
        comision_id: 'c1',
        estado: 'atrasado',
        actividades_pendientes: 3,
      },
    ]
    server.use(http.get(`${BASE}/api/alumnos/monitor`, () => HttpResponse.json(data)))
    const { useMonitorGeneral } = await import('./useMonitorGeneral')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMonitorGeneral(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty when no alumnos in monitor (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/alumnos/monitor`, () => HttpResponse.json([])))
    const { useMonitorGeneral } = await import('./useMonitorGeneral')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMonitorGeneral(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useMonitorEntregas ────────────────────────────────────────────────────────
describe('useMonitorEntregas', () => {
  it('fetches entregas sin corregir', async () => {
    const data = [
      {
        alumno_id: 'u2',
        nombre: 'María',
        apellido: 'García',
        legajo: '67890',
        actividad_id: 'a1',
        actividad_nombre: 'TP1',
        comision_id: 'c1',
        fecha_entrega: '2024-05-01',
      },
    ]
    server.use(
      http.get(`${BASE}/api/calificaciones/entregas-sin-corregir`, () =>
        HttpResponse.json(data),
      ),
    )
    const { useMonitorEntregas } = await import('./useMonitorEntregas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMonitorEntregas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty when all entregas corrected (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/calificaciones/entregas-sin-corregir`, () =>
        HttpResponse.json([]),
      ),
    )
    const { useMonitorEntregas } = await import('./useMonitorEntregas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMonitorEntregas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})
