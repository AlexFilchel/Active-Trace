import { describe, it, expect, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
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

afterEach(() => server.resetHandlers())

// ── 1.3 useLiquidaciones ─────────────────────────────────────────────────────
describe('useLiquidaciones', () => {
  it('fetches liquidaciones when periodo is provided', async () => {
    const data = [
      { id: 'l1', periodo: '2024-06', estado: 'ABIERTA', total_honorarios: 5000, total_docentes: 3 },
    ]
    server.use(http.get(`${BASE}/api/liquidaciones`, () => HttpResponse.json(data)))
    const { useLiquidaciones } = await import('./useLiquidaciones')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useLiquidaciones('2024-06'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('stays idle when periodo is undefined (triangulate)', async () => {
    const { useLiquidaciones } = await import('./useLiquidaciones')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useLiquidaciones(undefined), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    expect(result.current.data).toBeUndefined()
  })
})

// ── 1.4 useHistorialLiquidaciones ────────────────────────────────────────────
describe('useHistorialLiquidaciones', () => {
  it('fetches historial list', async () => {
    const data = [
      { id: 'h1', periodo: '2024-05', estado: 'CERRADA', total_honorarios: 4000, total_docentes: 2 },
    ]
    server.use(http.get(`${BASE}/api/liquidaciones/historial`, () => HttpResponse.json(data)))
    const { useHistorialLiquidaciones } = await import('./useHistorialLiquidaciones')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useHistorialLiquidaciones(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when historial is empty (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/liquidaciones/historial`, () => HttpResponse.json([])))
    const { useHistorialLiquidaciones } = await import('./useHistorialLiquidaciones')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useHistorialLiquidaciones(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── 1.5 useCerrarLiquidacion ─────────────────────────────────────────────────
describe('useCerrarLiquidacion', () => {
  it('calls PUT /api/liquidaciones/{id}/cerrar on mutate', async () => {
    let called = false
    server.use(
      http.put(`${BASE}/api/liquidaciones/l1/cerrar`, () => {
        called = true
        return HttpResponse.json({ id: 'l1', estado: 'CERRADA' })
      }),
    )
    const { useCerrarLiquidacion } = await import('./useCerrarLiquidacion')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCerrarLiquidacion(), { wrapper })
    await act(async () => {
      result.current.mutate('l1')
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(called).toBe(true)
  })

  it('mutation returns the updated liquidacion (triangulate)', async () => {
    const closed = { id: 'l2', estado: 'CERRADA', total_honorarios: 9000, total_docentes: 5 }
    server.use(http.put(`${BASE}/api/liquidaciones/l2/cerrar`, () => HttpResponse.json(closed)))
    const { useCerrarLiquidacion } = await import('./useCerrarLiquidacion')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCerrarLiquidacion(), { wrapper })
    await act(async () => {
      result.current.mutate('l2')
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(closed)
  })
})

// ── 1.6 useGrillasSalariales ─────────────────────────────────────────────────
describe('useGrillasSalariales', () => {
  it('fetches grilla salarial list', async () => {
    const data = [{ id: 'g1', categoria: 'JTP', salario_base: 2000 }]
    server.use(http.get(`${BASE}/api/salarios/grilla`, () => HttpResponse.json(data)))
    const { useGrillasSalariales } = await import('./useGrillasSalariales')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useGrillasSalariales(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no grillas exist (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/salarios/grilla`, () => HttpResponse.json([])))
    const { useGrillasSalariales } = await import('./useGrillasSalariales')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useGrillasSalariales(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useCrearGrilla', () => {
  it('posts to /api/salarios/grilla', async () => {
    const created = { id: 'g2', categoria: 'Titular', salario_base: 3000 }
    server.use(http.post(`${BASE}/api/salarios/grilla`, () => HttpResponse.json(created, { status: 201 })))
    const { useCrearGrilla } = await import('./useCrearGrilla')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearGrilla(), { wrapper })
    await act(async () => {
      result.current.mutate({ categoria: 'Titular', salario_base: 3000 })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(created)
  })

  it('mutation error surfaces when server returns 500 (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/salarios/grilla`, () => HttpResponse.json({ detail: 'error' }, { status: 500 })))
    const { useCrearGrilla } = await import('./useCrearGrilla')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearGrilla(), { wrapper })
    await act(async () => {
      result.current.mutate({ categoria: 'X', salario_base: 0 })
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useActualizarGrilla', () => {
  it('puts to /api/salarios/grilla/{id}', async () => {
    const updated = { id: 'g1', categoria: 'JTP', salario_base: 2500 }
    server.use(http.put(`${BASE}/api/salarios/grilla/g1`, () => HttpResponse.json(updated)))
    const { useActualizarGrilla } = await import('./useActualizarGrilla')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarGrilla(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'g1', data: { categoria: 'JTP', salario_base: 2500 } })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(updated)
  })

  it('returns updated data with new salario (triangulate)', async () => {
    const updated = { id: 'g3', categoria: 'Ayudante', salario_base: 1200 }
    server.use(http.put(`${BASE}/api/salarios/grilla/g3`, () => HttpResponse.json(updated)))
    const { useActualizarGrilla } = await import('./useActualizarGrilla')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarGrilla(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'g3', data: { categoria: 'Ayudante', salario_base: 1200 } })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.salario_base).toBe(1200)
  })
})

describe('useEliminarGrilla', () => {
  it('deletes /api/salarios/grilla/{id}', async () => {
    let called = false
    server.use(
      http.delete(`${BASE}/api/salarios/grilla/g1`, () => {
        called = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { useEliminarGrilla } = await import('./useEliminarGrilla')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarGrilla(), { wrapper })
    await act(async () => {
      result.current.mutate('g1')
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(called).toBe(true)
  })

  it('is error when server returns 404 (triangulate)', async () => {
    server.use(http.delete(`${BASE}/api/salarios/grilla/notfound`, () => new HttpResponse(null, { status: 404 })))
    const { useEliminarGrilla } = await import('./useEliminarGrilla')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarGrilla(), { wrapper })
    await act(async () => {
      result.current.mutate('notfound')
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 1.7 useFacturas ──────────────────────────────────────────────────────────
describe('useFacturas', () => {
  it('fetches facturas list', async () => {
    const data = [{ id: 'f1', proveedor: 'ACME', monto: 500, descripcion: 'Servicio', estado: 'PENDIENTE', fecha: '2024-06-01' }]
    server.use(http.get(`${BASE}/api/facturas`, () => HttpResponse.json(data)))
    const { useFacturas } = await import('./useFacturas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useFacturas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no facturas (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/facturas`, () => HttpResponse.json([])))
    const { useFacturas } = await import('./useFacturas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useFacturas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useCrearFactura', () => {
  it('posts to /api/facturas', async () => {
    const created = { id: 'f2', proveedor: 'XYZ', monto: 1000, descripcion: 'Insumos', estado: 'PENDIENTE', fecha: '2024-06-02' }
    server.use(http.post(`${BASE}/api/facturas`, () => HttpResponse.json(created, { status: 201 })))
    const { useCrearFactura } = await import('./useCrearFactura')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearFactura(), { wrapper })
    await act(async () => {
      result.current.mutate({ proveedor: 'XYZ', monto: 1000, descripcion: 'Insumos' })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.proveedor).toBe('XYZ')
  })

  it('surfaces error on 400 (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/facturas`, () => HttpResponse.json({ detail: 'bad' }, { status: 400 })))
    const { useCrearFactura } = await import('./useCrearFactura')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearFactura(), { wrapper })
    await act(async () => {
      result.current.mutate({ proveedor: '', monto: -1, descripcion: '' })
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useActualizarEstadoFactura', () => {
  it('puts estado to /api/facturas/{id}/estado', async () => {
    const updated = { id: 'f1', proveedor: 'ACME', monto: 500, descripcion: 'Srv', estado: 'APROBADA', fecha: '2024-06-01' }
    server.use(http.put(`${BASE}/api/facturas/f1/estado`, () => HttpResponse.json(updated)))
    const { useActualizarEstadoFactura } = await import('./useActualizarEstadoFactura')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarEstadoFactura(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'f1', estado: 'APROBADA' })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.estado).toBe('APROBADA')
  })

  it('handles RECHAZADA estado (triangulate)', async () => {
    const updated = { id: 'f3', proveedor: 'Y', monto: 200, descripcion: 'Z', estado: 'RECHAZADA', fecha: '2024-06-03' }
    server.use(http.put(`${BASE}/api/facturas/f3/estado`, () => HttpResponse.json(updated)))
    const { useActualizarEstadoFactura } = await import('./useActualizarEstadoFactura')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarEstadoFactura(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'f3', estado: 'RECHAZADA' })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.estado).toBe('RECHAZADA')
  })
})
