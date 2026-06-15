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

// ── 2.3 useCarreras ──────────────────────────────────────────────────────────
describe('useCarreras', () => {
  it('fetches carreras list', async () => {
    const data = [{ id: 'c1', nombre: 'Ingeniería', codigo: 'ING' }]
    server.use(http.get(`${BASE}/api/carreras`, () => HttpResponse.json(data)))
    const { useCarreras } = await import('./useCarreras')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCarreras(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no carreras (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/carreras`, () => HttpResponse.json([])))
    const { useCarreras } = await import('./useCarreras')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCarreras(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useCrearCarrera', () => {
  it('posts to /api/carreras', async () => {
    const created = { id: 'c2', nombre: 'Licenciatura', codigo: 'LIC' }
    server.use(http.post(`${BASE}/api/carreras`, () => HttpResponse.json(created, { status: 201 })))
    const { useCrearCarrera } = await import('./useCrearCarrera')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearCarrera(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: 'Licenciatura', codigo: 'LIC' }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.nombre).toBe('Licenciatura')
  })

  it('surfaces error on 500 (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/carreras`, () => HttpResponse.json({}, { status: 500 })))
    const { useCrearCarrera } = await import('./useCrearCarrera')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearCarrera(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: '' }) })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useActualizarCarrera', () => {
  it('puts to /api/carreras/{id}', async () => {
    const updated = { id: 'c1', nombre: 'Ingeniería Updated', codigo: 'ING' }
    server.use(http.put(`${BASE}/api/carreras/c1`, () => HttpResponse.json(updated)))
    const { useActualizarCarrera } = await import('./useActualizarCarrera')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarCarrera(), { wrapper })
    await act(async () => { result.current.mutate({ id: 'c1', data: { nombre: 'Ingeniería Updated' } }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.nombre).toBe('Ingeniería Updated')
  })

  it('returns updated data (triangulate)', async () => {
    const updated = { id: 'c3', nombre: 'Arquitectura', codigo: 'ARQ' }
    server.use(http.put(`${BASE}/api/carreras/c3`, () => HttpResponse.json(updated)))
    const { useActualizarCarrera } = await import('./useActualizarCarrera')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useActualizarCarrera(), { wrapper })
    await act(async () => { result.current.mutate({ id: 'c3', data: { nombre: 'Arquitectura' } }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.codigo).toBe('ARQ')
  })
})

describe('useEliminarCarrera', () => {
  it('deletes /api/carreras/{id}', async () => {
    let called = false
    server.use(http.delete(`${BASE}/api/carreras/c1`, () => { called = true; return new HttpResponse(null, { status: 204 }) }))
    const { useEliminarCarrera } = await import('./useEliminarCarrera')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarCarrera(), { wrapper })
    await act(async () => { result.current.mutate('c1') })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(called).toBe(true)
  })

  it('errors on 404 (triangulate)', async () => {
    server.use(http.delete(`${BASE}/api/carreras/nope`, () => new HttpResponse(null, { status: 404 })))
    const { useEliminarCarrera } = await import('./useEliminarCarrera')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarCarrera(), { wrapper })
    await act(async () => { result.current.mutate('nope') })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 2.4 useCohortes ──────────────────────────────────────────────────────────
describe('useCohortes', () => {
  it('fetches cohortes list', async () => {
    const data = [{ id: 'ch1', nombre: '2024', carrera_id: 'c1', anio: 2024 }]
    server.use(http.get(`${BASE}/api/cohortes`, () => HttpResponse.json(data)))
    const { useCohortes } = await import('./useCohortes')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCohortes(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty array when no cohortes (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/cohortes`, () => HttpResponse.json([])))
    const { useCohortes } = await import('./useCohortes')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCohortes(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useCrearCohorte', () => {
  it('posts to /api/cohortes', async () => {
    const created = { id: 'ch2', nombre: '2025', carrera_id: 'c1', anio: 2025 }
    server.use(http.post(`${BASE}/api/cohortes`, () => HttpResponse.json(created, { status: 201 })))
    const { useCrearCohorte } = await import('./useCrearCohorte')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearCohorte(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: '2025', carrera_id: 'c1', anio: 2025 }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.anio).toBe(2025)
  })

  it('errors on 400 (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/cohortes`, () => HttpResponse.json({}, { status: 400 })))
    const { useCrearCohorte } = await import('./useCrearCohorte')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearCohorte(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: '', carrera_id: '', anio: 0 }) })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useEliminarCohorte', () => {
  it('deletes /api/cohortes/{id}', async () => {
    let called = false
    server.use(http.delete(`${BASE}/api/cohortes/ch1`, () => { called = true; return new HttpResponse(null, { status: 204 }) }))
    const { useEliminarCohorte } = await import('./useEliminarCohorte')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarCohorte(), { wrapper })
    await act(async () => { result.current.mutate('ch1') })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(called).toBe(true)
  })

  it('errors on 404 (triangulate)', async () => {
    server.use(http.delete(`${BASE}/api/cohortes/nope`, () => new HttpResponse(null, { status: 404 })))
    const { useEliminarCohorte } = await import('./useEliminarCohorte')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarCohorte(), { wrapper })
    await act(async () => { result.current.mutate('nope') })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 2.5 useMaterias ──────────────────────────────────────────────────────────
describe('useMaterias', () => {
  it('fetches materias list', async () => {
    const data = [{ id: 'm1', nombre: 'Matemáticas', carrera_id: 'c1' }]
    server.use(http.get(`${BASE}/api/materias`, () => HttpResponse.json(data)))
    const { useMaterias } = await import('./useMaterias')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMaterias(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('returns empty when no materias (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/materias`, () => HttpResponse.json([])))
    const { useMaterias } = await import('./useMaterias')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMaterias(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useCrearMateria', () => {
  it('posts to /api/materias', async () => {
    const created = { id: 'm2', nombre: 'Física', carrera_id: 'c1' }
    server.use(http.post(`${BASE}/api/materias`, () => HttpResponse.json(created, { status: 201 })))
    const { useCrearMateria } = await import('./useCrearMateria')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearMateria(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: 'Física', carrera_id: 'c1' }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.nombre).toBe('Física')
  })

  it('errors on server failure (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/materias`, () => HttpResponse.json({}, { status: 500 })))
    const { useCrearMateria } = await import('./useCrearMateria')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearMateria(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: '', carrera_id: '' }) })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useEliminarMateria', () => {
  it('deletes /api/materias/{id}', async () => {
    let called = false
    server.use(http.delete(`${BASE}/api/materias/m1`, () => { called = true; return new HttpResponse(null, { status: 204 }) }))
    const { useEliminarMateria } = await import('./useEliminarMateria')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarMateria(), { wrapper })
    await act(async () => { result.current.mutate('m1') })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(called).toBe(true)
  })

  it('errors on 404 (triangulate)', async () => {
    server.use(http.delete(`${BASE}/api/materias/nope`, () => new HttpResponse(null, { status: 404 })))
    const { useEliminarMateria } = await import('./useEliminarMateria')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEliminarMateria(), { wrapper })
    await act(async () => { result.current.mutate('nope') })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── 2.6 useUsuarios ──────────────────────────────────────────────────────────
describe('useUsuarios', () => {
  it('fetches usuarios list', async () => {
    const data = [{ id: 'u1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', roles: ['PROFESOR'], activo: true }]
    server.use(http.get(`${BASE}/api/usuarios`, () => HttpResponse.json(data)))
    const { useUsuarios } = await import('./useUsuarios')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUsuarios(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.[0].email).toBe('ana@t.com')
  })

  it('returns empty when no usuarios (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/usuarios`, () => HttpResponse.json([])))
    const { useUsuarios } = await import('./useUsuarios')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUsuarios(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

describe('useCrearUsuario', () => {
  it('posts to /api/usuarios', async () => {
    const created = { id: 'u2', nombre: 'Carlos', apellido: 'Ruiz', email: 'c@t.com', roles: ['TUTOR'], activo: true }
    server.use(http.post(`${BASE}/api/usuarios`, () => HttpResponse.json(created, { status: 201 })))
    const { useCrearUsuario } = await import('./useCrearUsuario')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearUsuario(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: 'Carlos', apellido: 'Ruiz', email: 'c@t.com', password: 'pass', roles: ['TUTOR'] }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.email).toBe('c@t.com')
  })

  it('errors on 400 (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/usuarios`, () => HttpResponse.json({}, { status: 400 })))
    const { useCrearUsuario } = await import('./useCrearUsuario')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCrearUsuario(), { wrapper })
    await act(async () => { result.current.mutate({ nombre: '', apellido: '', email: '', password: '', roles: [] }) })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useAsignarRoles', () => {
  it('posts to /api/usuarios/{id}/roles', async () => {
    const updated = { id: 'u1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', roles: ['ADMIN'], activo: true }
    server.use(http.post(`${BASE}/api/usuarios/u1/roles`, () => HttpResponse.json(updated)))
    const { useAsignarRoles } = await import('./useAsignarRoles')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAsignarRoles(), { wrapper })
    await act(async () => { result.current.mutate({ id: 'u1', roles: ['ADMIN'] }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.roles).toContain('ADMIN')
  })

  it('roles assignment with multiple roles (triangulate)', async () => {
    const updated = { id: 'u2', nombre: 'X', apellido: 'Y', email: 'x@y.com', roles: ['COORDINADOR', 'FINANZAS'], activo: true }
    server.use(http.post(`${BASE}/api/usuarios/u2/roles`, () => HttpResponse.json(updated)))
    const { useAsignarRoles } = await import('./useAsignarRoles')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAsignarRoles(), { wrapper })
    await act(async () => { result.current.mutate({ id: 'u2', roles: ['COORDINADOR', 'FINANZAS'] }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.roles).toHaveLength(2)
  })
})

// ── 2.7 useAuditoriaLog + useAuditoriaMetricas ───────────────────────────────
describe('useAuditoriaLog', () => {
  it('fetches log with no filters', async () => {
    const data = { items: [{ id: 'a1', accion: 'LOGIN', usuario_email: 'u@t.com', modulo: 'auth', timestamp: '2024-06-01T10:00:00' }], total: 1, page: 1, page_size: 20 }
    server.use(http.get(`${BASE}/api/auditoria/log`, () => HttpResponse.json(data)))
    const { useAuditoriaLog } = await import('./useAuditoriaLog')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAuditoriaLog({}, 1), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items).toHaveLength(1)
  })

  it('passes accion filter as query param (triangulate)', async () => {
    let receivedParams: URLSearchParams | null = null
    server.use(
      http.get(`${BASE}/api/auditoria/log`, ({ request }) => {
        receivedParams = new URL(request.url).searchParams
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 })
      }),
    )
    const { useAuditoriaLog } = await import('./useAuditoriaLog')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAuditoriaLog({ accion: 'LOGIN' }, 1), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(receivedParams?.get('accion')).toBe('LOGIN')
  })
})

describe('useAuditoriaMetricas', () => {
  it('fetches metricas', async () => {
    const data = { total_eventos_hoy: 42, total_eventos_semana: 200, acciones_frecuentes: [], usuarios_activos_hoy: 5 }
    server.use(http.get(`${BASE}/api/auditoria/metricas`, () => HttpResponse.json(data)))
    const { useAuditoriaMetricas } = await import('./useAuditoriaMetricas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAuditoriaMetricas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_eventos_hoy).toBe(42)
  })

  it('returns data with usuarios_activos_hoy (triangulate)', async () => {
    const data = { total_eventos_hoy: 10, total_eventos_semana: 100, acciones_frecuentes: [{ accion: 'VIEW', count: 5 }], usuarios_activos_hoy: 3 }
    server.use(http.get(`${BASE}/api/auditoria/metricas`, () => HttpResponse.json(data)))
    const { useAuditoriaMetricas } = await import('./useAuditoriaMetricas')
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useAuditoriaMetricas(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.usuarios_activos_hoy).toBe(3)
    expect(result.current.data?.acciones_frecuentes).toHaveLength(1)
  })
})
