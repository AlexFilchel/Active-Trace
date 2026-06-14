# Tasks: C-15 — Avisos y Acknowledgment

> Strict TDD por tarea de test: Safety Net → RED → GREEN → TRIANGULATE → REFACTOR. No mockear la DB.

## 0. Safety Net

- [x] 0.1 Correr suite existente y capturar baseline. Si algo falla, reportar como pre-existing, no arreglar.

## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/avisos.py` con `Aviso` y `AcknowledgmentAviso` (ambos heredan `TenantScopedMixin`):
  - `Aviso`: alcance (varchar 20), materia_id (UUID FK nullable), cohorte_id (UUID FK nullable), rol_destino (varchar 50 nullable), severidad (varchar 20), titulo (varchar 255), cuerpo (Text), inicio_en (DateTime tz), fin_en (DateTime tz), orden (int default 0), activo (bool default True), requiere_ack (bool default False).
  - `AcknowledgmentAviso`: aviso_id (UUID FK→aviso CASCADE), usuario_id (UUID FK→usuario RESTRICT), confirmado_at (DateTime tz default now).
  - `__table_args__`: índices en `aviso.materia_id`, `aviso.cohorte_id`, `aviso.inicio_en`; en `acknowledgment_aviso.aviso_id`, `acknowledgment_aviso.usuario_id`; UniqueConstraint `(tenant_id, aviso_id, usuario_id)` en `AcknowledgmentAviso`. **NO** declarar `ix_<tabla>_tenant_id` (lo crea el mixin).
- [x] 1.2 Registrar `Aviso` y `AcknowledgmentAviso` en `backend/app/models/__init__.py`.
- [x] 1.3 Crear `backend/alembic/versions/012_avisos_acknowledgment.py` (revision `012_avisos_acknowledgment`, down_revision `011_evaluaciones_coloquios`):
  - Tablas `aviso` y `acknowledgment_aviso` con FKs y UniqueConstraint.
  - Índices del 1.1.
  - Seed idempotente: permiso `avisos:publicar` por tenant; asignarlo a roles COORDINADOR y ADMIN (patrón `ON CONFLICT DO NOTHING` de `009_comunicaciones.py`).
  - `downgrade()`: drop tablas en orden inverso de FK + borrar permiso/asignaciones.

## 2. Schemas Pydantic (`extra='forbid'`)

- [x] 2.1 Crear `backend/app/schemas/avisos.py`:
  - `CrearAvisoRequest`: alcance, materia_id?, cohorte_id?, rol_destino?, severidad, titulo, cuerpo, inicio_en, fin_en, orden (default 0), activo (default True), requiere_ack (default False). Validar `fin_en > inicio_en`.
  - `EditarAvisoRequest`: todos los campos opcionales; validar `fin_en > inicio_en` si ambos presentes.
  - `AvisoResponse`: todos los campos de `Aviso` más `acusado: bool` (derivado).
  - `AvisoGestionResponse`: igual a `AvisoResponse` más `total_acks: int` (derivado).
  - `AckResponse`: `aviso_id`, `usuario_id`, `confirmado_at`, `ya_existia: bool`.
  - `MetricasAvisoResponse`: `aviso_id`, `titulo`, `requiere_ack`, `total_acks`.

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/avisos.py`:
  - `AvisoRepository(TenantScopedRepository[Aviso])`: `create`, `get`, `list` (todos del tenant), `list_activos_vigentes(now)` (filtra `activo=True`, `inicio_en <= now <= fin_en`, `deleted_at IS NULL`), `update`.
  - `AckRepository(TenantScopedRepository[AcknowledgmentAviso])`: `create(aviso_id, usuario_id)`, `existe(aviso_id, usuario_id) -> bool`, `count_by_aviso(aviso_id) -> int`.

## 4. Service

- [x] 4.1 Crear `backend/app/services/aviso_service.py` con `AvisoService(session, tenant_id)`.
  - `_resolve_usuario(auth_user_id)` → `usuario.id` via `UsuarioRepository.get_by_auth_user_id()`.
  - `_get_asignaciones_vigentes(usuario_id)` → sets de `materia_id` y `cohorte_id` activos.
  - `_audiencia_incluye(aviso, roles, materia_ids, cohorte_ids) -> bool`: evalúa alcance/rol/materia/cohorte.
- [x] 4.2 `crear_aviso(actor_id, payload, ip)`: crear `Aviso` → audit `AVISO_CREAR` → 201.
- [x] 4.3 `editar_aviso(actor_id, aviso_id, payload, ip)`: validar del tenant (404 si no) → update → audit `AVISO_EDITAR` → 200.
- [x] 4.4 `listar_gestion()`: todos los avisos del tenant + `total_acks` derivado.
- [x] 4.5 `listar_mis_avisos(auth_user_id, roles, incluir_acusados)`: resolver usuario → asignaciones vigentes → `list_activos_vigentes(now)` → filtrar por audiencia → filtrar por ack (RN-19) → campo `acusado` por aviso → ordenar orden ASC / inicio_en DESC.
- [x] 4.6 `ack(auth_user_id, aviso_id, ip)`: validar aviso existe + activo + vigente + `requiere_ack=True` (422 si no) → `AckRepository.existe()` → si ya existe: 200 idempotente; si no: crear ack + audit `AVISO_ACK` → 201.
- [x] 4.7 `metricas(aviso_id)`: get aviso del tenant (404 si no) → `count_by_aviso` → `MetricasAvisoResponse`.

## 5. Router

- [x] 5.1 Crear `backend/app/api/v1/routers/avisos.py` con `router = APIRouter(prefix="/api/avisos", tags=["avisos"])`:
  - `POST /api/avisos` → `crear_aviso` (201), permiso `avisos:publicar`.
  - `GET /api/avisos/gestion` → `listar_gestion`, permiso `avisos:publicar`. (**Registrar ANTES de `/{id}`** para evitar conflicto de rutas.)
  - `GET /api/avisos` → `listar_mis_avisos`, autenticado; query param `incluir_acusados: bool = False`.
  - `PATCH /api/avisos/{id}` → `editar_aviso`, permiso `avisos:publicar`.
  - `POST /api/avisos/{id}/ack` → `ack`, autenticado; 201 si nuevo, 200 si idempotente.
  - `GET /api/avisos/{id}/metricas` → `metricas`, permiso `avisos:publicar`.
- [x] 5.2 Registrar `avisos_router` en `backend/app/main.py`.

## 6. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 6.1 Test crear aviso: crea `Aviso` con todos los campos; audit `AVISO_CREAR`; sin permiso → 403; fin_en ≤ inicio_en → 422; campo extra → 422. Triangular: aviso PorMateria con materia_id, aviso PorRol con rol_destino.
- [x] 6.2 Test filtrado por vigencia (RN-18): aviso fuera de ventana (`now < inicio_en` o `now > fin_en`) no aparece en `GET /api/avisos`; aviso dentro sí aparece.
- [x] 6.3 Test filtrado por audiencia (RN-20): aviso Global → visible para cualquier rol; aviso PorRol → solo usuarios con ese rol; aviso PorMateria → solo usuarios con asignación vigente a esa materia; aviso PorCohorte → solo usuarios con asignación vigente a esa cohorte. Triangular: usuario sin asignación no ve PorMateria.
- [x] 6.4 Test ack: acusar aviso con `requiere_ack=True` crea `AcknowledgmentAviso` (201); segundo ack del mismo usuario → 200 idempotente, no duplica; tras ack el aviso NO aparece en listado del usuario; con `?incluir_acusados=true` sí aparece con `acusado=true`.
- [x] 6.5 Test ack inválido: ack en aviso sin `requiere_ack` → 422; ack en aviso fuera de vigencia → 422; ack en aviso de otro tenant → 404.
- [x] 6.6 Test gestión: `GET /api/avisos/gestion` devuelve todos (activos e inactivos, en y fuera de vigencia) con `total_acks`; tenant aislado (aviso de otro tenant no aparece); `PATCH /api/avisos/{id}` actualiza campos; `GET /api/avisos/{id}/metricas` devuelve count correcto.
- [x] 6.7 Test aviso inactivo: aviso con `activo=False` no aparece en `GET /api/avisos` aunque esté en vigencia; sí aparece en gestión.
