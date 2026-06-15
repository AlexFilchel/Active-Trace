import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── getAvisos ─────────────────────────────────────────────────────────────────
describe('avisosService.getAvisos', () => {
  it('returns list of avisos (happy path)', async () => {
    const data = [
      {
        id: 'av1',
        titulo: 'Aviso importante',
        cuerpo: 'Texto del aviso',
        scope: 'tenant',
        publicado: true,
        creado_en: '2024-01-01',
      },
    ]
    server.use(http.get(`${BASE}/api/avisos`, () => HttpResponse.json(data)))
    const { avisosService } = await import('./avisosService')
    const result = await avisosService.getAvisos()
    expect(result).toEqual(data)
  })

  it('returns empty list when no avisos (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/avisos`, () => HttpResponse.json([])))
    const { avisosService } = await import('./avisosService')
    const result = await avisosService.getAvisos()
    expect(result).toEqual([])
  })
})

// ── createAviso ───────────────────────────────────────────────────────────────
describe('avisosService.createAviso', () => {
  it('posts aviso data and returns created aviso', async () => {
    const payload = { titulo: 'Nuevo aviso', cuerpo: 'Contenido', scope: 'tenant' as const }
    const created = { id: 'av2', ...payload, publicado: false, creado_en: '2024-06-01' }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/avisos`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(created, { status: 201 })
      }),
    )
    const { avisosService } = await import('./avisosService')
    const result = await avisosService.createAviso(payload)
    expect(result).toEqual(created)
    expect(capturedBody).toMatchObject({ titulo: 'Nuevo aviso', scope: 'tenant' })
  })

  it('throws on validation error (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/avisos`, () =>
        HttpResponse.json({ detail: 'titulo required' }, { status: 422 }),
      ),
    )
    const { avisosService } = await import('./avisosService')
    await expect(
      avisosService.createAviso({ titulo: '', cuerpo: '', scope: 'tenant' }),
    ).rejects.toThrow()
  })
})

// ── deleteAviso ───────────────────────────────────────────────────────────────
describe('avisosService.deleteAviso', () => {
  it('sends DELETE request for aviso id', async () => {
    let deletedId = ''
    server.use(
      http.delete(`${BASE}/api/avisos/:id`, ({ params }) => {
        deletedId = params.id as string
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { avisosService } = await import('./avisosService')
    await avisosService.deleteAviso('av1')
    expect(deletedId).toBe('av1')
  })

  it('throws when aviso not found (triangulate)', async () => {
    server.use(
      http.delete(`${BASE}/api/avisos/:id`, () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
      ),
    )
    const { avisosService } = await import('./avisosService')
    await expect(avisosService.deleteAviso('non-existent')).rejects.toThrow()
  })
})

// ── getAcknowledgments ────────────────────────────────────────────────────────
describe('avisosService.getAcknowledgments', () => {
  it('returns acknowledgments for aviso', async () => {
    const acks = [
      { alumno_id: 'u1', nombre: 'Juan', apellido: 'Pérez', confirmado_en: '2024-06-10' },
    ]
    server.use(
      http.get(`${BASE}/api/avisos/:id/acknowledgments`, () => HttpResponse.json(acks)),
    )
    const { avisosService } = await import('./avisosService')
    const result = await avisosService.getAcknowledgments('av1')
    expect(result).toEqual(acks)
  })

  it('returns empty when no acknowledgments yet (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/avisos/:id/acknowledgments`, () => HttpResponse.json([])),
    )
    const { avisosService } = await import('./avisosService')
    const result = await avisosService.getAcknowledgments('av2')
    expect(result).toEqual([])
  })
})
