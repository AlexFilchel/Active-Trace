import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── getEncuentros ─────────────────────────────────────────────────────────────
describe('encuentrosService.getEncuentros', () => {
  it('returns list of encuentros (happy path)', async () => {
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
    const { encuentrosService } = await import('./encuentrosService')
    const result = await encuentrosService.getEncuentros()
    expect(result).toEqual(data)
  })

  it('returns empty list when no encuentros (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/encuentros`, () => HttpResponse.json([])))
    const { encuentrosService } = await import('./encuentrosService')
    const result = await encuentrosService.getEncuentros()
    expect(result).toEqual([])
  })
})

// ── createEncuentro ───────────────────────────────────────────────────────────
describe('encuentrosService.createEncuentro', () => {
  it('posts encuentro data and returns created encuentro', async () => {
    const payload = {
      titulo: 'Clase 2',
      fecha: '2024-08-08',
      hora_inicio: '18:00',
      hora_fin: '20:00',
      comision_id: 'c1',
      tipo: 'clase' as const,
    }
    const created = { id: 'en2', ...payload }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/encuentros`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(created, { status: 201 })
      }),
    )
    const { encuentrosService } = await import('./encuentrosService')
    const result = await encuentrosService.createEncuentro(payload)
    expect(result).toEqual(created)
    expect(capturedBody).toMatchObject({ titulo: 'Clase 2', tipo: 'clase' })
  })

  it('throws on missing required fields (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/encuentros`, () =>
        HttpResponse.json({ detail: 'fecha required' }, { status: 422 }),
      ),
    )
    const { encuentrosService } = await import('./encuentrosService')
    await expect(
      encuentrosService.createEncuentro({
        titulo: '',
        fecha: '',
        hora_inicio: '',
        hora_fin: '',
        comision_id: '',
        tipo: 'clase',
      }),
    ).rejects.toThrow()
  })
})

// ── getGuardias ───────────────────────────────────────────────────────────────
describe('encuentrosService.getGuardias', () => {
  it('returns list of guardias', async () => {
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
    const { encuentrosService } = await import('./encuentrosService')
    const result = await encuentrosService.getGuardias()
    expect(result).toEqual(data)
  })

  it('returns empty list when no guardias (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/guardias`, () => HttpResponse.json([])))
    const { encuentrosService } = await import('./encuentrosService')
    const result = await encuentrosService.getGuardias()
    expect(result).toEqual([])
  })
})
