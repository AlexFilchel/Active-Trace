import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── 2.1 getActividades ───────────────────────────────────────────────────────
describe('comisionesService.getActividades', () => {
  it('fetches actividades for a comision (happy path)', async () => {
    const data = [{ id: 'a1', nombre: 'TP1', tipo: 'tp' }]
    server.use(
      http.get(`${BASE}/api/calificaciones/actividades`, ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('comision_id') === 'c1') {
          return HttpResponse.json(data)
        }
        return HttpResponse.json([], { status: 200 })
      }),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getActividades('c1')
    expect(result).toEqual(data)
  })

  it('filters by tipo when provided (triangulate)', async () => {
    const data = [{ id: 'a2', nombre: 'Quiz', tipo: 'quiz' }]
    server.use(
      http.get(`${BASE}/api/calificaciones/actividades`, ({ request }) => {
        const url = new URL(request.url)
        if (
          url.searchParams.get('comision_id') === 'c2' &&
          url.searchParams.get('tipo') === 'quiz'
        ) {
          return HttpResponse.json(data)
        }
        return HttpResponse.json([])
      }),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getActividades('c2', 'quiz')
    expect(result).toEqual(data)
  })
})

// ── 2.2 importarCalificaciones ───────────────────────────────────────────────
describe('comisionesService.importarCalificaciones', () => {
  it('posts multipart/form-data and returns result', async () => {
    const responseData = { importados: 10, errores: 0 }
    let capturedContentType = ''
    server.use(
      http.post(`${BASE}/api/calificaciones/importar`, async ({ request }) => {
        capturedContentType = request.headers.get('content-type') ?? ''
        return HttpResponse.json(responseData)
      }),
    )
    const { comisionesService } = await import('./comisionesService')
    const file = new File(['col1,col2'], 'notas.csv', { type: 'text/csv' })
    const result = await comisionesService.importarCalificaciones('c1', file, ['a1', 'a2'])
    expect(result).toEqual(responseData)
    expect(capturedContentType).toContain('multipart/form-data')
  })

  it('throws on server error (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/calificaciones/importar`, () =>
        HttpResponse.json({ detail: 'Bad file' }, { status: 422 }),
      ),
    )
    const { comisionesService } = await import('./comisionesService')
    const file = new File(['bad'], 'bad.csv', { type: 'text/csv' })
    await expect(comisionesService.importarCalificaciones('c1', file, [])).rejects.toThrow()
  })
})

// ── 2.3 getUmbral / putUmbral ────────────────────────────────────────────────
describe('comisionesService.getUmbral', () => {
  it('returns umbral config', async () => {
    const config = { comision_id: 'c1', umbral_pct: 60, valores_aprobatorios: [6, 7, 8, 9, 10] }
    server.use(
      http.get(`${BASE}/api/calificaciones/umbral`, ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('comision_id') === 'c1') return HttpResponse.json(config)
        return HttpResponse.json(null, { status: 404 })
      }),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getUmbral('c1')
    expect(result).toEqual(config)
  })

  it('throws 404 for unknown comision (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/calificaciones/umbral`, () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
      ),
    )
    const { comisionesService } = await import('./comisionesService')
    await expect(comisionesService.getUmbral('unknown')).rejects.toThrow()
  })
})

describe('comisionesService.putUmbral', () => {
  it('updates umbral config and returns updated config', async () => {
    const updated = { comision_id: 'c1', umbral_pct: 70, valores_aprobatorios: [7, 8, 9, 10] }
    server.use(
      http.put(`${BASE}/api/calificaciones/umbral`, () => HttpResponse.json(updated)),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.putUmbral('c1', 70, [7, 8, 9, 10])
    expect(result).toEqual(updated)
  })

  it('throws on validation error (triangulate)', async () => {
    server.use(
      http.put(`${BASE}/api/calificaciones/umbral`, () =>
        HttpResponse.json({ detail: 'Invalid' }, { status: 422 }),
      ),
    )
    const { comisionesService } = await import('./comisionesService')
    await expect(comisionesService.putUmbral('c1', 200, [])).rejects.toThrow()
  })
})

// ── 2.4 Analysis endpoints ───────────────────────────────────────────────────
describe('comisionesService.getAtrasados', () => {
  it('returns list of atrasados', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'Juan', apellido: 'Doe', legajo: '12345', actividades_pendientes: ['tp1'], motivo: 'Sin entregar' }]
    server.use(
      http.get(`${BASE}/api/atrasados`, () => HttpResponse.json(data)),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getAtrasados('c1')
    expect(result).toEqual(data)
  })

  it('returns empty list when no atrasados (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/atrasados`, () => HttpResponse.json([])),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getAtrasados('c2')
    expect(result).toEqual([])
  })
})

describe('comisionesService.getRanking', () => {
  it('returns ranking list', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'Ana', apellido: 'Gomez', legajo: '99', promedio: 9.5, posicion: 1 }]
    server.use(
      http.get(`${BASE}/api/analisis/ranking`, () => HttpResponse.json(data)),
    )
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getRanking('c1')
    expect(result).toEqual(data)
  })

  it('returns empty ranking (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/analisis/ranking`, () => HttpResponse.json([])))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getRanking('c1')).toEqual([])
  })
})

describe('comisionesService.getNotasFinales', () => {
  it('returns notas finales list', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'Lu', apellido: 'Ro', legajo: '1', nota_final: 8, estado: 'Aprobado' }]
    server.use(http.get(`${BASE}/api/calificaciones/notas-finales`, () => HttpResponse.json(data)))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getNotasFinales('c1')).toEqual(data)
  })

  it('returns empty list (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/calificaciones/notas-finales`, () => HttpResponse.json([])))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getNotasFinales('c1')).toEqual([])
  })
})

describe('comisionesService.getReporteRapido', () => {
  it('returns reporte rapido summary', async () => {
    const data = { total_alumnos: 20, aprobados: 15, reprobados: 3, sin_nota: 2, atrasados: 5, promedio_general: 7.2 }
    server.use(http.get(`${BASE}/api/analisis/reporte-rapido`, () => HttpResponse.json(data)))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getReporteRapido('c1')).toEqual(data)
  })

  it('returns null promedio when no data (triangulate)', async () => {
    const data = { total_alumnos: 0, aprobados: 0, reprobados: 0, sin_nota: 0, atrasados: 0, promedio_general: null }
    server.use(http.get(`${BASE}/api/analisis/reporte-rapido`, () => HttpResponse.json(data)))
    const { comisionesService } = await import('./comisionesService')
    const result = await comisionesService.getReporteRapido('c1')
    expect(result.promedio_general).toBeNull()
  })
})

describe('comisionesService.getEntregasSinCorregir', () => {
  it('returns list of entregas sin corregir', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'P', apellido: 'Q', legajo: '2', actividad_id: 'a1', actividad_nombre: 'TP1', fecha_entrega: '2024-01-01' }]
    server.use(http.get(`${BASE}/api/analisis/entregas-sin-corregir`, () => HttpResponse.json(data)))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getEntregasSinCorregir('c1')).toEqual(data)
  })

  it('returns empty list (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/analisis/entregas-sin-corregir`, () => HttpResponse.json([])))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getEntregasSinCorregir('c1')).toEqual([])
  })
})

// ── 2.5 Comunicaciones endpoints ─────────────────────────────────────────────
describe('comisionesService.previewComunicacion', () => {
  it('returns preview data', async () => {
    const preview = { asunto: 'Alerta', cuerpo: 'Estás atrasado', destinatarios_count: 3 }
    server.use(http.post(`${BASE}/api/comunicaciones/preview`, () => HttpResponse.json(preview)))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.previewComunicacion('c1', 'atraso')).toEqual(preview)
  })

  it('throws on server error (triangulate)', async () => {
    server.use(http.post(`${BASE}/api/comunicaciones/preview`, () => HttpResponse.json({ detail: 'err' }, { status: 500 })))
    const { comisionesService } = await import('./comisionesService')
    await expect(comisionesService.previewComunicacion('c1', 'atraso')).rejects.toThrow()
  })
})

describe('comisionesService.enviarComunicacion', () => {
  it('enqueues communication and returns ok', async () => {
    const res = { encolados: 3, mensaje: 'OK' }
    server.use(http.post(`${BASE}/api/comunicaciones/enviar`, () => HttpResponse.json(res)))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.enviarComunicacion('c1', 'atraso')).toEqual(res)
  })

  it('sends optional custom message (triangulate)', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post(`${BASE}/api/comunicaciones/enviar`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ encolados: 2, mensaje: 'OK' })
      }),
    )
    const { comisionesService } = await import('./comisionesService')
    await comisionesService.enviarComunicacion('c1', 'atraso', 'Texto extra')
    expect((capturedBody as { mensaje_personalizado?: string }).mensaje_personalizado).toBe('Texto extra')
  })
})

describe('comisionesService.getEstadoComunicaciones', () => {
  it('returns estado list', async () => {
    const data = [{ alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', estado: 'Pendiente' }]
    server.use(http.get(`${BASE}/api/comunicaciones/estado`, () => HttpResponse.json(data)))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getEstadoComunicaciones('c1')).toEqual(data)
  })

  it('returns empty when no comunicaciones sent yet (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/comunicaciones/estado`, () => HttpResponse.json([])))
    const { comisionesService } = await import('./comisionesService')
    expect(await comisionesService.getEstadoComunicaciones('c1')).toEqual([])
  })
})
