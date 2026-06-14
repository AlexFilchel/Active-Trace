# Tasks: C-19 — Panel Auditoría y Métricas

> Strict TDD por tarea de test: Safety Net → RED → GREEN → TRIANGULATE → REFACTOR. No mockear la DB.
> Governance ALTO: implementar con checkpoints; surfacear decisiones no obvias.
> Permiso `auditoria:ver` nuevo — seed en migración 015 (sin DDL de tablas).

## 0. Safety Net

- [x] 0.1 Correr suite existente y capturar baseline. Reportar pre-existing failures sin arreglarlos.

## 1. Migración (solo seed, sin DDL)

- [x] 1.1 Crear `backend/alembic/versions/015_auditoria_permiso.py` (revision `015_auditoria_permiso`, down_revision `014_programas_fechas_academicas`):
  - Seed del permiso `auditoria:ver` para roles ADMIN, COORDINADOR y FINANZAS en cada tenant.
  - `ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING`.
  - `downgrade()`: no-op (permiso puede quedar, no rompe nada).

## 2. Schemas Pydantic (`extra='forbid'`)

- [x] 2.1 Crear `backend/app/schemas/auditoria.py`:
  - `AccionPorDiaResponse`: `fecha` (date), `total` (int).
  - `EstadoComunicacionResponse`: `actor_id` (UUID), `accion` (str), `total` (int).
  - `InteraccionDocenteResponse`: `actor_id` (UUID), `accion` (str), `total` (int).
  - `AuditLogResponse`: `id` (UUID), `actor_id` (UUID), `tenant_id` (UUID), `accion` (str), `filas_afectadas` (int | None), `detalle` (dict | None), `ip` (str | None), `created_at` (datetime). Con `from_attributes=True`.

## 3. Repository

- [x] 3.1 Crear `backend/app/repositories/auditoria.py` con `AuditoriaRepository(session, tenant_id)`:
  - `acciones_por_dia(desde?, hasta?, actor_id?, materia_id?)` → `list[dict]` con GROUP BY `DATE(created_at)`.
  - `estado_comunicaciones(actor_id?)` → `list[dict]` con `WHERE accion LIKE 'COMUNICACION_%'` + GROUP BY `actor_id, accion`.
  - `interacciones_docente(desde?, hasta?, actor_id?, materia_id?)` → `list[dict]` GROUP BY `actor_id, accion`.
  - `log(desde?, hasta?, actor_id?, accion?, limit=200)` → `list[AuditLog]` ORDER BY `created_at` DESC LIMIT min(limit, 500).
  - Todas las queries filtran por `tenant_id` (NO heredar TenantScopedRepository — AuditLog no tiene soft-delete útil aquí).

## 4. Service

- [x] 4.1 Crear `backend/app/services/auditoria_service.py` con `AuditoriaService(session, tenant_id)`:
  - `_scope_actor_id(user_roles, user_auth_id, filtro_usuario_id?)` → resuelve el `actor_id` a filtrar:
    - Si el usuario tiene rol COORDINADOR (y NO ADMIN/FINANZAS): forzar `actor_id = user_auth_id` (scope propio, D2).
    - Si es ADMIN o FINANZAS: usar el `filtro_usuario_id` si se pasó, o None (sin restricción).
  - `acciones_por_dia(user, desde?, hasta?, materia_id?, usuario_id?)` → llama al repo con el actor_id resuelto.
  - `estado_comunicaciones(user)` → llama al repo con el actor_id resuelto.
  - `interacciones_docente(user, desde?, hasta?, materia_id?, usuario_id?)` → llama al repo con el actor_id resuelto.
  - `log(user, desde?, hasta?, accion?, usuario_id?, limit=200)` → llama al repo con el actor_id resuelto.

## 5. Router

- [x] 5.1 Crear `backend/app/api/v1/routers/auditoria.py`:
  - `router = APIRouter(prefix="/api/auditoria", tags=["auditoria"])`.
  - `GET /api/auditoria/acciones-por-dia` → `acciones_por_dia`, permiso `auditoria:ver`.
  - `GET /api/auditoria/estado-comunicaciones` → `estado_comunicaciones`, permiso `auditoria:ver`.
  - `GET /api/auditoria/interacciones-docente` → `interacciones_docente`, permiso `auditoria:ver`.
  - `GET /api/auditoria/log` → `log`, permiso `auditoria:ver`. Query param `limit: int = Query(default=200, ge=1, le=500)`.
- [x] 5.2 Registrar `auditoria_router` en `backend/app/main.py`.

## 6. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 6.1 Test acciones por día y scope: ADMIN ve todos los actores; COORDINADOR solo ve las propias; filtro por rango de fechas; sin permiso → 403. Triangular: filtro por `usuario_id` cuando es ADMIN.
- [x] 6.2 Test log paginado y filtros: log default ≤200; `limit=50` retorna 50; `limit=501` → 422; filtro por `accion`; COORDINADOR scope propio en log.
- [x] 6.3 Test estado comunicaciones e interacciones: estado-comunicaciones filtra solo acciones `COMUNICACION_*`; interacciones-docente agrupa correctamente; COORDINADOR solo ve las propias en ambos.
