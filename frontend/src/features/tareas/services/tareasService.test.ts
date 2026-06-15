import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'

const BASE = 'http://localhost:8000'

// ── getTareas ─────────────────────────────────────────────────────────────────
describe('tareasService.getTareas', () => {
  it('returns list of tareas (happy path)', async () => {
    const data = [
      {
        id: 't1',
        titulo: 'Revisar TP1',
        estado: 'pendiente',
        prioridad: 'alta',
        creado_en: '2024-01-01',
      },
    ]
    server.use(http.get(`${BASE}/api/tareas`, () => HttpResponse.json(data)))
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.getTareas()
    expect(result).toEqual(data)
  })

  it('returns empty list when no tareas (triangulate)', async () => {
    server.use(http.get(`${BASE}/api/tareas`, () => HttpResponse.json([])))
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.getTareas()
    expect(result).toEqual([])
  })
})

// ── createTarea ───────────────────────────────────────────────────────────────
describe('tareasService.createTarea', () => {
  it('posts tarea data and returns created tarea', async () => {
    const payload = { titulo: 'Nueva tarea', prioridad: 'media' as const }
    const created = {
      id: 't2',
      titulo: 'Nueva tarea',
      estado: 'pendiente',
      prioridad: 'media',
      creado_en: '2024-06-01',
    }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/tareas`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(created, { status: 201 })
      }),
    )
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.createTarea(payload)
    expect(result).toEqual(created)
    expect(capturedBody).toMatchObject({ titulo: 'Nueva tarea' })
  })

  it('throws on missing titulo (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/tareas`, () =>
        HttpResponse.json({ detail: 'titulo required' }, { status: 422 }),
      ),
    )
    const { tareasService } = await import('./tareasService')
    await expect(tareasService.createTarea({ titulo: '' })).rejects.toThrow()
  })
})

// ── updateTarea ───────────────────────────────────────────────────────────────
describe('tareasService.updateTarea', () => {
  it('patches estado to en_progreso (workflow transition)', async () => {
    const updated = {
      id: 't1',
      titulo: 'Revisar TP1',
      estado: 'en_progreso',
      prioridad: 'alta',
      creado_en: '2024-01-01',
    }
    let capturedBody: unknown
    server.use(
      http.put(`${BASE}/api/tareas/:id`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(updated)
      }),
    )
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.updateTarea('t1', { estado: 'en_progreso' })
    expect(result.estado).toBe('en_progreso')
    expect(capturedBody).toMatchObject({ estado: 'en_progreso' })
  })

  it('transitions from en_progreso to completada (triangulate)', async () => {
    const updated = {
      id: 't1',
      titulo: 'Revisar TP1',
      estado: 'completada',
      prioridad: 'alta',
      creado_en: '2024-01-01',
    }
    server.use(
      http.put(`${BASE}/api/tareas/:id`, async () => HttpResponse.json(updated)),
    )
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.updateTarea('t1', { estado: 'completada' })
    expect(result.estado).toBe('completada')
  })
})

// ── getComentarios / addComentario ────────────────────────────────────────────
describe('tareasService.getComentarios', () => {
  it('returns comments for a tarea', async () => {
    const comments = [
      {
        id: 'c1',
        tarea_id: 't1',
        autor_id: 'u1',
        autor_nombre: 'Ana',
        cuerpo: 'Listo',
        creado_en: '2024-06-10',
      },
    ]
    server.use(
      http.get(`${BASE}/api/tareas/:id/comentarios`, () => HttpResponse.json(comments)),
    )
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.getComentarios('t1')
    expect(result).toEqual(comments)
  })

  it('returns empty list when no comments (triangulate)', async () => {
    server.use(
      http.get(`${BASE}/api/tareas/:id/comentarios`, () => HttpResponse.json([])),
    )
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.getComentarios('t2')
    expect(result).toEqual([])
  })
})

describe('tareasService.addComentario', () => {
  it('posts comment body and returns new comment', async () => {
    const newComment = {
      id: 'c2',
      tarea_id: 't1',
      autor_id: 'u2',
      autor_nombre: 'Bot',
      cuerpo: 'Revisando',
      creado_en: '2024-06-11',
    }
    let capturedBody: unknown
    server.use(
      http.post(`${BASE}/api/tareas/:id/comentarios`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(newComment, { status: 201 })
      }),
    )
    const { tareasService } = await import('./tareasService')
    const result = await tareasService.addComentario('t1', 'Revisando')
    expect(result).toEqual(newComment)
    expect(capturedBody).toMatchObject({ cuerpo: 'Revisando' })
  })

  it('throws on server error (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/tareas/:id/comentarios`, () =>
        HttpResponse.json({ detail: 'Error' }, { status: 500 }),
      ),
    )
    const { tareasService } = await import('./tareasService')
    await expect(tareasService.addComentario('t1', '')).rejects.toThrow()
  })
})
