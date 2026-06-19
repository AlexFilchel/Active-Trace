import { apiClient } from '@/shared/services/api'
import type {
  Actividad,
  UmbralConfig,
  AlumnoAtrasado,
  RankingItem,
  NotaFinal,
  EntregaSinCorregir,
  ReporteRapido,
  EstadoDestinatario,
  ComunicacionPreview,
  ImportacionResult,
  ComisionId,
} from '../types'

export const comisionesService = {
  // ── C-10: Calificaciones (requieren comision_id = materia_id) ────────────

  async getActividades(comisionId: ComisionId, tipo?: string): Promise<Actividad[]> {
    const params: Record<string, string> = { comision_id: comisionId }
    if (tipo) params.tipo = tipo
    const res = await apiClient.get<Actividad[]>('/api/calificaciones/actividades', { params })
    return res.data
  },

  async importarCalificaciones(
    comisionId: ComisionId,
    file: File,
    actividades: string[],
  ): Promise<ImportacionResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('comision_id', comisionId)
    actividades.forEach((a) => formData.append('actividades[]', a))
    const res = await apiClient.post<ImportacionResult>(
      '/api/calificaciones/importar',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return res.data
  },

  async getUmbral(comisionId: ComisionId): Promise<UmbralConfig> {
    const res = await apiClient.get<UmbralConfig>('/api/calificaciones/umbral', {
      params: { comision_id: comisionId },
    })
    return res.data
  },

  async putUmbral(
    comisionId: ComisionId,
    umbralPct: number,
    valoresAprobatorios: number[],
  ): Promise<UmbralConfig> {
    const res = await apiClient.put<UmbralConfig>('/api/calificaciones/umbral', {
      comision_id: comisionId,
      umbral_pct: umbralPct,
      valores_aprobatorios: valoresAprobatorios,
    })
    return res.data
  },

  // ── C-11: Análisis (scope automático por JWT, sin comision_id) ───────────

  async getAtrasados(): Promise<AlumnoAtrasado[]> {
    const tipoLabel: Record<string, string> = {
      nota_bajo_umbral: 'Nota bajo umbral',
      sin_entrega: 'Sin entrega',
      sin_nota: 'Sin nota',
    }
    const res = await apiClient.get<{ items: any[] }>('/api/analisis/atrasados')
    return (res.data.items ?? []).map((item: any) => {
      const motivos: any[] = item.motivos ?? []
      const tiposUnicos = [...new Set(motivos.map((m: any) => tipoLabel[m.tipo] ?? m.tipo))]
      return {
        alumno_id: item.entrada_padron_id,
        nombre: item.nombre,
        apellido: item.apellidos,
        legajo: item.comision ?? '',
        actividades_pendientes: motivos.map((m: any) => m.actividad),
        motivo: tiposUnicos.join(', '),
      }
    })
  },

  async getRanking(): Promise<RankingItem[]> {
    const res = await apiClient.get<{ items: any[] }>('/api/analisis/ranking-aprobadas')
    return (res.data.items ?? []).map((item: any, idx: number) => ({
      alumno_id: item.entrada_padron_id,
      nombre: item.nombre,
      apellido: item.apellidos,
      legajo: item.comision ?? '',
      promedio: item.aprobadas_count ?? 0,
      posicion: idx + 1,
    }))
  },

  async getNotasFinales(): Promise<NotaFinal[]> {
    const res = await apiClient.get<{ items: any[] }>('/api/analisis/notas-finales')
    return (res.data.items ?? []).map((item: any) => ({
      alumno_id: item.entrada_padron_id,
      nombre: item.nombre,
      apellido: item.apellidos,
      legajo: item.comision ?? '',
      nota_final: item.tiene_nota_final ? parseFloat(item.nota_final) : null,
      estado: item.tiene_nota_final ? 'con_nota' : 'sin_nota',
    }))
  },

  async getReporteRapido(): Promise<ReporteRapido> {
    const res = await apiClient.get<any>('/api/analisis/materia/resumen')
    const activos = res.data.alumnos_activos ?? 0
    const atrasados = res.data.alumnos_atrasados ?? 0
    return {
      total_alumnos: activos,
      aprobados: activos - atrasados,
      reprobados: atrasados,
      sin_nota: 0,
      atrasados,
      promedio_general: null,
    }
  },

  async getEntregasSinCorregir(): Promise<EntregaSinCorregir[]> {
    // El backend solo expone export CSV para este dato; retornamos vacío.
    return []
  },

  // ── C-12: Comunicaciones ─────────────────────────────────────────────────

  async previewComunicacion(comisionId: ComisionId, tipo: string): Promise<ComunicacionPreview> {
    const res = await apiClient.post<ComunicacionPreview>('/api/comunicaciones/preview', {
      comision_id: comisionId,
      tipo,
    })
    return res.data
  },

  async enviarComunicacion(
    comisionId: ComisionId,
    tipo: string,
    mensajePersonalizado?: string,
  ): Promise<{ encolados: number; mensaje: string }> {
    const body: Record<string, unknown> = { comision_id: comisionId, tipo }
    if (mensajePersonalizado !== undefined) body.mensaje_personalizado = mensajePersonalizado
    const res = await apiClient.post<{ encolados: number; mensaje: string }>(
      '/api/comunicaciones/enviar',
      body,
    )
    return res.data
  },

  async getEstadoComunicaciones(comisionId: ComisionId): Promise<EstadoDestinatario[]> {
    const res = await apiClient.get<EstadoDestinatario[]>('/api/comunicaciones/estado', {
      params: { comision_id: comisionId },
    })
    return res.data
  },
}
