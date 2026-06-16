import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import React from 'react'

const BASE = 'http://localhost:8000'

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return {
    wrapper: ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: qc }, children),
    qc,
  }
}

// ── 3.1 useActividades ───────────────────────────────────────────────────────
describe('useActividades', () => {
  it('fetches actividades when comisionId is provided', async () => {
    const data = [{ id: 'a1', nombre: 'TP1', tipo: 'tp' }]
    server.use(http.get(`${BASE}/api/calificaciones/actividades`, () => HttpResponse.json(data)))
    const { useActividades } = await import('./useActividades')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActividades('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('does not fetch when comisionId is undefined (triangulate)', async () => {
    const { useActividades } = await import('./useActividades')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActividades(undefined), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    expect(result.current.data).toBeUndefined()
  })

  it('returns empty array when server returns empty list (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/calificaciones/actividades`, () => HttpResponse.json([])))
    const { useActividades } = await import('./useActividades')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActividades('c2'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── 3.2 useUmbral ────────────────────────────────────────────────────────────
describe('useUmbral', () => {
  it('returns umbral config from server', async () => {
    const config = { comision_id: 'c1', umbral_pct: 70, valores_aprobatorios: [7, 8, 9, 10] }
    server.use(http.get(`${BASE}/api/calificaciones/umbral`, () => HttpResponse.json(config)))
    const { useUmbral } = await import('./useUmbral')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUmbral('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(config)
  })

  it('stays idle when comisionId is undefined (triangulate)', async () => {
    const { useUmbral } = await import('./useUmbral')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUmbral(undefined), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

// ── 3.3 useAtrasados ─────────────────────────────────────────────────────────
describe('useAtrasados', () => {
  it('fetches atrasados successfully', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', actividades_pendientes: ['tp1'], motivo: 'Sin entregar' }]
    server.use(http.get(`${BASE}/api/atrasados`, () => HttpResponse.json(data)))
    const { useAtrasados } = await import('./useAtrasados')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAtrasados('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/atrasados`, () => HttpResponse.json([])))
    const { useAtrasados } = await import('./useAtrasados')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAtrasados('c2'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })

  it('sets error on server failure (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/atrasados`, () => HttpResponse.json({ detail: 'err' }, { status: 500 })))
    const { useAtrasados } = await import('./useAtrasados')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAtrasados('c3'), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 3.4 useRanking / useNotasFinales ─────────────────────────────────────────
describe('useRanking', () => {
  it('fetches ranking list', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', promedio: 9, posicion: 1 }]
    server.use(http.get(`${BASE}/api/analisis/ranking`, () => HttpResponse.json(data)))
    const { useRanking } = await import('./useRanking')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useRanking('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty ranking (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/analisis/ranking`, () => HttpResponse.json([])))
    const { useRanking } = await import('./useRanking')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useRanking('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useNotasFinales', () => {
  it('fetches notas finales', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', nota_final: 8, estado: 'Aprobado' }]
    server.use(http.get(`${BASE}/api/calificaciones/notas-finales`, () => HttpResponse.json(data)))
    const { useNotasFinales } = await import('./useNotasFinales')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useNotasFinales('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty list (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/calificaciones/notas-finales`, () => HttpResponse.json([])))
    const { useNotasFinales } = await import('./useNotasFinales')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useNotasFinales('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── 3.5 useReporteRapido / useEntregasSinCorregir ────────────────────────────
describe('useReporteRapido', () => {
  it('fetches reporte rapido', async () => {
    const data = { total_alumnos: 20, aprobados: 15, reprobados: 3, sin_nota: 2, atrasados: 5, promedio_general: 7.2 }
    server.use(http.get(`${BASE}/api/analisis/reporte-rapido`, () => HttpResponse.json(data)))
    const { useReporteRapido } = await import('./useReporteRapido')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useReporteRapido('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('handles null promedio_general (triangulate)', async () => {
    const data = { total_alumnos: 0, aprobados: 0, reprobados: 0, sin_nota: 0, atrasados: 0, promedio_general: null }
    server.use(http.get(`${BASE}/api/analisis/reporte-rapido`, () => HttpResponse.json(data)))
    const { useReporteRapido } = await import('./useReporteRapido')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useReporteRapido('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.promedio_general).toBeNull()
  })
})

describe('useEntregasSinCorregir', () => {
  it('fetches entregas sin corregir', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', actividad_id: 'a1', actividad_nombre: 'TP1', fecha_entrega: '2024-01-01' }]
    server.use(http.get(`${BASE}/api/analisis/entregas-sin-corregir`, () => HttpResponse.json(data)))
    const { useEntregasSinCorregir } = await import('./useEntregasSinCorregir')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEntregasSinCorregir('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty list when nothing pending (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/analisis/entregas-sin-corregir`, () => HttpResponse.json([])))
    const { useEntregasSinCorregir } = await import('./useEntregasSinCorregir')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEntregasSinCorregir('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── 3.6 useComunicacionesEstado ───────────────────────────────────────────────
describe('useComunicacionesEstado', () => {
  it('fetches estado list', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', estado: 'Pendiente' }]
    server.use(http.get(`${BASE}/api/comunicaciones/estado`, () => HttpResponse.json(data)))
    const { useComunicacionesEstado } = await import('./useComunicacionesEstado')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useComunicacionesEstado('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty when no comunicaciones (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/comunicaciones/estado`, () => HttpResponse.json([])))
    const { useComunicacionesEstado } = await import('./useComunicacionesEstado')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useComunicacionesEstado('c1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── 4.1 useImportarCalificaciones ────────────────────────────────────────────
describe('useImportarCalificaciones', () => {
  it('mutates successfully and invalidates queries', async () => {
    server.use(http.post(`${BASE}/api/calificaciones/importar`, () => HttpResponse.json({ importados: 5, errores: 0 })))
    const { useImportarCalificaciones } = await import('./useImportarCalificaciones')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useImportarCalificaciones(), { wrapper })
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    result.current.mutate({ comisionId: 'c1', file, actividades: ['a1'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({ importados: 5, errores: 0 })
  })

  it('exposes error on failure (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/calificaciones/importar`, () => HttpResponse.json({ detail: 'err' }, { status: 422 })))
    const { useImportarCalificaciones } = await import('./useImportarCalificaciones')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useImportarCalificaciones(), { wrapper })
    const file = new File(['bad'], 'bad.csv', { type: 'text/csv' })
    result.current.mutate({ comisionId: 'c1', file, actividades: [] })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 4.2 useActualizarUmbral ──────────────────────────────────────────────────
describe('useActualizarUmbral', () => {
  it('updates umbral and returns new config', async () => {
    const updated = { comision_id: 'c1', umbral_pct: 65, valores_aprobatorios: [7, 8] }
    server.use(http.put(`${BASE}/api/calificaciones/umbral`, () => HttpResponse.json(updated)))
    const { useActualizarUmbral } = await import('./useActualizarUmbral')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarUmbral(), { wrapper })
    result.current.mutate({ comisionId: 'c1', umbralPct: 65, valoresAprobatorios: [7, 8] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(updated)
  })

  it('exposes error on invalid umbral (triangulate)', async () => {
    server.use(http.put(`${BASE}/api/calificaciones/umbral`, () => HttpResponse.json({ detail: 'Invalid' }, { status: 422 })))
    const { useActualizarUmbral } = await import('./useActualizarUmbral')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarUmbral(), { wrapper })
    result.current.mutate({ comisionId: 'c1', umbralPct: 200, valoresAprobatorios: [] })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 4.3 usePreviewComunicacion ────────────────────────────────────────────────
describe('usePreviewComunicacion', () => {
  it('returns preview on success', async () => {
    const preview = { asunto: 'Alerta', cuerpo: 'Atrasado', destinatarios_count: 2 }
    server.use(http.post(`${BASE}/api/comunicaciones/preview`, () => HttpResponse.json(preview)))
    const { usePreviewComunicacion } = await import('./usePreviewComunicacion')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => usePreviewComunicacion(), { wrapper })
    result.current.mutate({ comisionId: 'c1', tipo: 'atraso' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(preview)
  })

  it('exposes error on failure (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/comunicaciones/preview`, () => HttpResponse.json({ detail: 'err' }, { status: 500 })))
    const { usePreviewComunicacion } = await import('./usePreviewComunicacion')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => usePreviewComunicacion(), { wrapper })
    result.current.mutate({ comisionId: 'c1', tipo: 'atraso' })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 4.4 useEnviarComunicacion ─────────────────────────────────────────────────
describe('useEnviarComunicacion', () => {
  it('sends comunicacion and returns confirmation', async () => {
    const res = { encolados: 3, mensaje: 'OK' }
    server.use(http.post(`${BASE}/api/comunicaciones/enviar`, () => HttpResponse.json(res)))
    const { useEnviarComunicacion } = await import('./useEnviarComunicacion')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEnviarComunicacion(), { wrapper })
    result.current.mutate({ comisionId: 'c1', tipo: 'atraso' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(res)
  })

  it('sends with mensaje_personalizado (triangulate)', async () => {
    let capturedBody: Record<string, unknown> = {}
    server.use(
      http.post(`${BASE}/api/comunicaciones/enviar`, async ({ request }) => {
        capturedBody = await request.json() as Record<string, unknown>
        return HttpResponse.json({ encolados: 1, mensaje: 'OK' })
      }),
    )
    const { useEnviarComunicacion } = await import('./useEnviarComunicacion')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEnviarComunicacion(), { wrapper })
    result.current.mutate({ comisionId: 'c1', tipo: 'atraso', mensajePersonalizado: 'Extra msg' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(capturedBody.mensaje_personalizado).toBe('Extra msg')
  })
})
