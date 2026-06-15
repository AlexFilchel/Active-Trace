import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── getMonitorGeneral ─────────────────────────────────────────────────────────
describe('monitoresService.getMonitorGeneral', () => {
  it('returns monitor items without filters (happy path)', async () => {
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
    const { monitoresService } = await import('./monitoresService')
    const result = await monitoresService.getMonitorGeneral()
    expect(result).toEqual(data)
  })

  it('passes comision_id filter in query params (triangulate)', async () => {
    let capturedParam = ''
    server.use(
      http.get(`${BASE}/api/alumnos/monitor`, ({ request }) => {
        const url = new URL(request.url)
        capturedParam = url.searchParams.get('comision_id') ?? ''
        return HttpResponse.json([])
      }),
    )
    const { monitoresService } = await import('./monitoresService')
    await monitoresService.getMonitorGeneral({ comision_id: 'c99' })
    expect(capturedParam).toBe('c99')
  })
})

// ── getMonitorEntregas ────────────────────────────────────────────────────────
describe('monitoresService.getMonitorEntregas', () => {
  it('returns entregas sin corregir (happy path)', async () => {
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
    const { monitoresService } = await import('./monitoresService')
    const result = await monitoresService.getMonitorEntregas()
    expect(result).toEqual(data)
  })

  it('returns empty list when all entregas corrected (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/calificaciones/entregas-sin-corregir`, () =>
        HttpResponse.json([]),
      ),
    )
    const { monitoresService } = await import('./monitoresService')
    const result = await monitoresService.getMonitorEntregas()
    expect(result).toEqual([])
  })
})
