import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── getEquipos ────────────────────────────────────────────────────────────────
describe('equiposService.getEquipos', () => {
  it('returns list of equipos (happy path)', async () => {
    const data = [
      { id: 'e1', nombre: 'Equipo A', vigente: true, creado_en: '2024-01-01' },
    ]
    server.use(http.get(`${BASE}/api/equipos`, () => HttpResponse.json(data)))
    const { equiposService } = await import('./equiposService')
    const result = await equiposService.getEquipos()
    expect(result).toEqual(data)
  })

  it('returns empty list when no equipos exist (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/equipos`, () => HttpResponse.json([])))
    const { equiposService } = await import('./equiposService')
    const result = await equiposService.getEquipos()
    expect(result).toEqual([])
  })
})

// ── createEquipo ──────────────────────────────────────────────────────────────
describe('equiposService.createEquipo', () => {
  it('posts data and returns created equipo', async () => {
    const payload = { nombre: 'Equipo B', vigente: true }
    const created = { id: 'e2', nombre: 'Equipo B', vigente: true, creado_en: '2024-01-01' }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/equipos`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(created, { status: 201 })
      }),
    )
    const { equiposService } = await import('./equiposService')
    const result = await equiposService.createEquipo(payload)
    expect(result).toEqual(created)
    expect(capturedBody).toMatchObject({ nombre: 'Equipo B' })
  })

  it('throws on validation error (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/equipos`, () =>
        HttpResponse.json({ detail: 'nombre required' }, { status: 422 }),
      ),
    )
    const { equiposService } = await import('./equiposService')
    await expect(equiposService.createEquipo({ nombre: '' })).rejects.toThrow()
  })
})

// ── deleteEquipo ──────────────────────────────────────────────────────────────
describe('equiposService.deleteEquipo', () => {
  it('sends DELETE request for equipo id', async () => {
    let deletedId = ''
    server.use(
      http.delete(`${BASE}/api/equipos/:id`, ({ params }) => {
        deletedId = params.id as string
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { equiposService } = await import('./equiposService')
    await equiposService.deleteEquipo('e1')
    expect(deletedId).toBe('e1')
  })

  it('throws when equipo not found (triangulate)', async () => {
    server.use(
      http.delete(`${BASE}/api/equipos/:id`, () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
      ),
    )
    const { equiposService } = await import('./equiposService')
    await expect(equiposService.deleteEquipo('non-existent')).rejects.toThrow()
  })
})

// ── clonarEquipo ──────────────────────────────────────────────────────────────
describe('equiposService.clonarEquipo', () => {
  it('posts clone payload and returns new equipo', async () => {
    const cloned = { id: 'e3', nombre: 'Equipo C', vigente: true, creado_en: '2024-06-01' }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/equipos/:id/clonar`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(cloned, { status: 201 })
      }),
    )
    const { equiposService } = await import('./equiposService')
    const result = await equiposService.clonarEquipo('e1', { nombre: 'Equipo C' })
    expect(result).toEqual(cloned)
    expect(capturedBody).toMatchObject({ nombre: 'Equipo C' })
  })

  it('throws when source equipo not found (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/equipos/:id/clonar`, () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
      ),
    )
    const { equiposService } = await import('./equiposService')
    await expect(
      equiposService.clonarEquipo('non-existent', { nombre: 'Clone' }),
    ).rejects.toThrow()
  })
})

// ── getMiembros ───────────────────────────────────────────────────────────────
describe('equiposService.getMiembros', () => {
  it('returns members for equipo', async () => {
    const members = [
      { usuario_id: 'u1', nombre: 'Ana', apellido: 'López', email: 'ana@x.com', rol: 'TUTOR' },
    ]
    server.use(
      http.get(`${BASE}/api/equipos/:id/miembros`, () => HttpResponse.json(members)),
    )
    const { equiposService } = await import('./equiposService')
    const result = await equiposService.getMiembros('e1')
    expect(result).toEqual(members)
  })

  it('returns empty when equipo has no members (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/equipos/:id/miembros`, () => HttpResponse.json([])),
    )
    const { equiposService } = await import('./equiposService')
    const result = await equiposService.getMiembros('e2')
    expect(result).toEqual([])
  })
})
