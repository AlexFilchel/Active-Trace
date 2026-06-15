import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── getColoquios ──────────────────────────────────────────────────────────────
describe('coloquiosService.getColoquios', () => {
  it('returns list of coloquios (happy path)', async () => {
    const data = [
      {
        id: 'col1',
        materia: 'Programación I',
        comision_id: 'c1',
        fecha_convocatoria: '2024-12-01',
        estado: 'abierto',
        creado_en: '2024-11-01',
      },
    ]
    server.use(http.get(`${BASE}/api/coloquios`, () => HttpResponse.json(data)))
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.getColoquios()
    expect(result).toEqual(data)
  })

  it('returns empty list when no coloquios (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/coloquios`, () => HttpResponse.json([])))
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.getColoquios()
    expect(result).toEqual([])
  })
})

// ── createColoquio ────────────────────────────────────────────────────────────
describe('coloquiosService.createColoquio', () => {
  it('posts coloquio and returns created coloquio', async () => {
    const payload = {
      materia: 'Matemáticas',
      comision_id: 'c1',
      fecha_convocatoria: '2024-12-15',
    }
    const created = { id: 'col2', ...payload, estado: 'abierto', creado_en: '2024-11-15' }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/coloquios`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(created, { status: 201 })
      }),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.createColoquio(payload)
    expect(result).toEqual(created)
    expect(capturedBody).toMatchObject({ materia: 'Matemáticas' })
  })

  it('throws on validation error (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/coloquios`, () =>
        HttpResponse.json({ detail: 'materia required' }, { status: 422 }),
      ),
    )
    const { coloquiosService } = await import('./coloquiosService')
    await expect(
      coloquiosService.createColoquio({ materia: '', comision_id: '', fecha_convocatoria: '' }),
    ).rejects.toThrow()
  })
})

// ── getDias / addDia ──────────────────────────────────────────────────────────
describe('coloquiosService.getDias', () => {
  it('returns dias for coloquio', async () => {
    const dias = [
      { id: 'd1', coloquio_id: 'col1', fecha: '2024-12-20', cupo_maximo: 10, inscritos: 3 },
    ]
    server.use(
      http.get(`${BASE}/api/coloquios/:id/dias`, () => HttpResponse.json(dias)),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.getDias('col1')
    expect(result).toEqual(dias)
  })

  it('returns empty when no dias added (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/coloquios/:id/dias`, () => HttpResponse.json([])),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.getDias('col2')
    expect(result).toEqual([])
  })
})

// ── getCandidatos ─────────────────────────────────────────────────────────────
describe('coloquiosService.getCandidatos', () => {
  it('returns candidatos for coloquio', async () => {
    const candidatos = [
      { alumno_id: 'u1', nombre: 'Pedro', apellido: 'Suárez', legajo: '11111' },
    ]
    server.use(
      http.get(`${BASE}/api/coloquios/:id/candidatos`, () => HttpResponse.json(candidatos)),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.getCandidatos('col1')
    expect(result).toEqual(candidatos)
  })

  it('returns empty when no candidatos (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/coloquios/:id/candidatos`, () => HttpResponse.json([])),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.getCandidatos('col2')
    expect(result).toEqual([])
  })
})

// ── setResultado ──────────────────────────────────────────────────────────────
describe('coloquiosService.setResultado', () => {
  it('puts resultado and returns updated candidato', async () => {
    const updated = {
      alumno_id: 'u1',
      nombre: 'Pedro',
      apellido: 'Suárez',
      legajo: '11111',
      resultado: 'aprobado',
    }
    let capturedBody: unknown
    server.use(
      http.put(
        `${BASE}/api/coloquios/:id/candidatos/:alumnoId/resultado`,
        async ({ request }) => {
          capturedBody = await request.json()
          return HttpResponse.json(updated)
        },
      ),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.setResultado('col1', 'u1', { resultado: 'aprobado' })
    expect(result.resultado).toBe('aprobado')
    expect(capturedBody).toMatchObject({ resultado: 'aprobado' })
  })

  it('sets desaprobado resultado (triangulate)', async () => {
    const updated = {
      alumno_id: 'u2',
      nombre: 'María',
      apellido: 'García',
      legajo: '22222',
      resultado: 'desaprobado',
    }
    server.use(
      http.put(
        `${BASE}/api/coloquios/:id/candidatos/:alumnoId/resultado`,
        async () => HttpResponse.json(updated),
      ),
    )
    const { coloquiosService } = await import('./coloquiosService')
    const result = await coloquiosService.setResultado('col1', 'u2', { resultado: 'desaprobado' })
    expect(result.resultado).toBe('desaprobado')
  })
})
