## 1. Schemas y contratos de API

- [x] 1.1 Crear `app/schemas/equipos.py` con los schemas Pydantic (extra='forbid'): `MisEquiposResponse`, `AsignacionFiltroQuery`, `AsignacionMasivaRequest`, `AsignacionMasivaResponse`, `ClonarEquipoRequest`, `ClonarEquipoResponse`, `VigenciaEquipoRequest`, `DocenteBusquedaItem`
- [x] 1.2 Agregar schema de exportación: `ExportarEquipoQuery` con `materia_id`, `carrera_id`, `cohorte_id` opcionales

## 2. Repository — extensiones sobre Asignacion

- [x] 2.1 En `app/repositories/asignacion_repository.py`, agregar `get_by_usuario(usuario_id, tenant_id)` que devuelve asignaciones del docente autenticado con joins a Materia, Carrera, Cohorte
- [x] 2.2 Agregar `list_by_equipo(tenant_id, materia_id, carrera_id, cohorte_id, filters)` con filtros opcionales por rol, estado y docente
- [x] 2.3 Agregar `bulk_create(asignaciones: list[Asignacion])` para inserción transaccional (usado por clonado y masiva)
- [x] 2.4 Agregar `bulk_update_vigencia(tenant_id, materia_id, carrera_id, cohorte_id, desde, hasta)` que retorna `rows_affected`
- [x] 2.5 Agregar `search_docentes(tenant_id, q, limit=20)` — búsqueda case-insensitive por nombre/apellido en Usuario, solo usuarios activos
- [x] 2.6 Agregar `get_vigentes_by_equipo(tenant_id, materia_id, carrera_id, cohorte_id)` — asignaciones con `estado_vigencia = activa` para el clonado

## 3. Service — lógica de negocio

- [x] 3.1 Crear `app/services/equipo_service.py` con `get_mis_equipos(usuario_id, tenant_id)`
- [x] 3.2 Agregar `list_asignaciones(tenant_id, filters)` con paginación
- [x] 3.3 Agregar `buscar_docentes(tenant_id, q)` — delega al repository
- [x] 3.4 Agregar `asignacion_masiva(tenant_id, actor_id, payload)`: crea asignaciones en bloque, detecta duplicados (409), registra `ASIGNACION_MODIFICAR` en AuditLog con `filas_afectadas`
- [x] 3.5 Agregar `clonar_equipo(tenant_id, actor_id, origen, destino)`: carga asignaciones vigentes del origen, crea nuevas con destino + nuevas fechas en transacción atómica, registra auditoría; lanza 422 si origen sin vigentes; rollback si falla cualquier inserción
- [x] 3.6 Agregar `modificar_vigencia_equipo(tenant_id, actor_id, payload)`: delega bulk_update al repository, registra `ASIGNACION_MODIFICAR` con `filas_afectadas`; lanza 404 si no hay asignaciones
- [x] 3.7 Agregar `exportar_equipo(tenant_id, filters)`: construye lista de asignaciones y genera contenido CSV

## 4. Router

- [x] 4.1 Crear `app/routers/equipos.py` y registrar en `app/main.py` bajo `/api/equipos`
- [x] 4.2 `GET /api/equipos/mis-equipos` — requiere `equipos:ver`; llama `get_mis_equipos`
- [x] 4.3 `GET /api/equipos/asignaciones` — requiere `equipos:asignar`; llama `list_asignaciones` con query params de filtro
- [x] 4.4 `GET /api/equipos/docentes/buscar` — requiere `equipos:asignar`; llama `buscar_docentes`
- [x] 4.5 `POST /api/equipos/asignaciones/masiva` — requiere `equipos:asignar`; llama `asignacion_masiva`
- [x] 4.6 `POST /api/equipos/clonar` — requiere `equipos:asignar`; llama `clonar_equipo`
- [x] 4.7 `PATCH /api/equipos/vigencia` — requiere `equipos:asignar`; llama `modificar_vigencia_equipo`
- [x] 4.8 `GET /api/equipos/exportar` — requiere `equipos:asignar`; llama `exportar_equipo`; devuelve `StreamingResponse` con Content-Disposition para descarga

## 5. Tests (Strict TDD — Red → Green → Triangulate → Refactor)

- [x] 5.1 Test `mis-equipos`: docente ve solo sus asignaciones del tenant; docente sin asignaciones recibe `[]`; aislamiento multi-tenant
- [x] 5.2 Test `list_asignaciones`: filtro por materia devuelve solo esa materia; usuario sin permiso `equipos:asignar` recibe 403
- [x] 5.3 Test `buscar_docentes`: búsqueda case-insensitive devuelve hasta 20; sin match devuelve `[]`
- [x] 5.4 Test `asignacion_masiva`: crea N asignaciones; 409 si docente ya asignado al mismo contexto; AuditLog con `filas_afectadas = N`
- [x] 5.5 Test `clonar_equipo`: clona N asignaciones vigentes con nuevas fechas; rollback si falla una inserción; 422 si origen sin vigentes; AuditLog con `filas_afectadas`
- [x] 5.6 Test `modificar_vigencia_equipo`: actualiza `desde`/`hasta` en todas las asignaciones del equipo; 404 si equipo inexistente; AuditLog registrado
- [x] 5.7 Test `exportar_equipo`: response con Content-Disposition y contenido CSV; exportación con 0 asignaciones devuelve solo headers
