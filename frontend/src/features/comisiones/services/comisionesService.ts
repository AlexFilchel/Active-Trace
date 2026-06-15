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
  // ── C-10: Calificaciones ──────────────────────────────────────────────────

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

  async getNotasFinales(comisionId: ComisionId): Promise<NotaFinal[]> {
    const res = await apiClient.get<NotaFinal[]>('/api/calificaciones/notas-finales', {
      params: { comision_id: comisionId },
    })
    return res.data
  },

  // ── C-11: Análisis ────────────────────────────────────────────────────────

  async getAtrasados(comisionId: ComisionId): Promise<AlumnoAtrasado[]> {
    const res = await apiClient.get<AlumnoAtrasado[]>('/api/atrasados', {
      params: { comision_id: comisionId },
    })
    return res.data
  },

  async getRanking(comisionId: ComisionId): Promise<RankingItem[]> {
    const res = await apiClient.get<RankingItem[]>('/api/analisis/ranking', {
      params: { comision_id: comisionId },
    })
    return res.data
  },

  async getEntregasSinCorregir(comisionId: ComisionId): Promise<EntregaSinCorregir[]> {
    const res = await apiClient.get<EntregaSinCorregir[]>('/api/analisis/entregas-sin-corregir', {
      params: { comision_id: comisionId },
    })
    return res.data
  },

  async getReporteRapido(comisionId: ComisionId): Promise<ReporteRapido> {
    const res = await apiClient.get<ReporteRapido>('/api/analisis/reporte-rapido', {
      params: { comision_id: comisionId },
    })
    return res.data
  },

  // ── C-12: Comunicaciones ──────────────────────────────────────────────────

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
