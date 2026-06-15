import { apiClient } from '@/shared/services/api'
import type {
  Carrera,
  CarreraCreate,
  Cohorte,
  CohorteCreate,
  Materia,
  MateriaCreate,
  Usuario,
  UsuarioCreate,
  UsuarioUpdate,
  RolUsuario,
  AuditoriaEntry,
  AuditoriaFiltros,
  AuditoriaMetricas,
  PaginatedResponse,
} from '../types'

export const adminService = {
  // ── Carreras ───────────────────────────────────────────────────────────────

  async getCarreras(): Promise<Carrera[]> {
    const res = await apiClient.get<Carrera[]>('/api/carreras')
    return res.data
  },

  async crearCarrera(data: CarreraCreate): Promise<Carrera> {
    const res = await apiClient.post<Carrera>('/api/carreras', data)
    return res.data
  },

  async actualizarCarrera(id: string, data: Partial<CarreraCreate>): Promise<Carrera> {
    const res = await apiClient.put<Carrera>(`/api/carreras/${id}`, data)
    return res.data
  },

  async eliminarCarrera(id: string): Promise<void> {
    await apiClient.delete(`/api/carreras/${id}`)
  },

  // ── Cohortes ───────────────────────────────────────────────────────────────

  async getCohortes(): Promise<Cohorte[]> {
    const res = await apiClient.get<Cohorte[]>('/api/cohortes')
    return res.data
  },

  async crearCohorte(data: CohorteCreate): Promise<Cohorte> {
    const res = await apiClient.post<Cohorte>('/api/cohortes', data)
    return res.data
  },

  async actualizarCohorte(id: string, data: Partial<CohorteCreate>): Promise<Cohorte> {
    const res = await apiClient.put<Cohorte>(`/api/cohortes/${id}`, data)
    return res.data
  },

  async eliminarCohorte(id: string): Promise<void> {
    await apiClient.delete(`/api/cohortes/${id}`)
  },

  // ── Materias ───────────────────────────────────────────────────────────────

  async getMaterias(): Promise<Materia[]> {
    const res = await apiClient.get<Materia[]>('/api/materias')
    return res.data
  },

  async crearMateria(data: MateriaCreate): Promise<Materia> {
    const res = await apiClient.post<Materia>('/api/materias', data)
    return res.data
  },

  async actualizarMateria(id: string, data: Partial<MateriaCreate>): Promise<Materia> {
    const res = await apiClient.put<Materia>(`/api/materias/${id}`, data)
    return res.data
  },

  async eliminarMateria(id: string): Promise<void> {
    await apiClient.delete(`/api/materias/${id}`)
  },

  // ── Usuarios ───────────────────────────────────────────────────────────────

  async getUsuarios(): Promise<Usuario[]> {
    const res = await apiClient.get<Usuario[]>('/api/usuarios')
    return res.data
  },

  async crearUsuario(data: UsuarioCreate): Promise<Usuario> {
    const res = await apiClient.post<Usuario>('/api/usuarios', data)
    return res.data
  },

  async actualizarUsuario(id: string, data: UsuarioUpdate): Promise<Usuario> {
    const res = await apiClient.put<Usuario>(`/api/usuarios/${id}`, data)
    return res.data
  },

  async getUsuario(id: string): Promise<Usuario> {
    const res = await apiClient.get<Usuario>(`/api/usuarios/${id}`)
    return res.data
  },

  async asignarRoles(id: string, roles: RolUsuario[]): Promise<Usuario> {
    const res = await apiClient.post<Usuario>(`/api/usuarios/${id}/roles`, { roles })
    return res.data
  },

  // ── Auditoría ──────────────────────────────────────────────────────────────

  async getAuditoriaLog(
    filtros: AuditoriaFiltros,
    page: number,
    pageSize = 20,
  ): Promise<PaginatedResponse<AuditoriaEntry>> {
    const params: Record<string, string | number> = { page, page_size: pageSize }
    if (filtros.accion) params.accion = filtros.accion
    if (filtros.usuario) params.usuario = filtros.usuario
    if (filtros.desde) params.desde = filtros.desde
    if (filtros.hasta) params.hasta = filtros.hasta
    if (filtros.modulo) params.modulo = filtros.modulo
    const res = await apiClient.get<PaginatedResponse<AuditoriaEntry>>('/api/auditoria/log', { params })
    return res.data
  },

  async getAuditoriaMetricas(): Promise<AuditoriaMetricas> {
    const res = await apiClient.get<AuditoriaMetricas>('/api/auditoria/metricas')
    return res.data
  },
}
