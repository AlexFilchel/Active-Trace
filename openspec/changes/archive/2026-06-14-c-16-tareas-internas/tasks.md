# Tasks: C-16 — Tareas Internas

> Strict TDD por tarea de test: Safety Net → RED → GREEN → TRIANGULATE → REFACTOR. No mockear la DB.

## 0. Safety Net

- [x] 0.1 Correr suite existente y capturar baseline. Si algo falla, reportar como pre-existing, no arreglar.

## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/tareas.py` con `Tarea` y `ComentarioTarea` (ambos heredan `TenantScopedMixin`):
  - `Tarea`: `materia_id` (UUID FK→materia nullable), `asignado_a` (UUID FK→usuario RESTRICT), `asignado_por` (UUID FK→usuario RESTRICT), `estado` (String 20, default `"Pendiente"`), `descripcion` (Text), `contexto_id` (UUID nullable, sin FK).
  - `__table_args__` en `Tarea`: índices en `asignado_a`, `asignado_por`, `materia_id`, `estado`. **NO** declarar `ix_tarea_tenant_id` (lo crea el mixin).
  - `ComentarioTarea`: `tarea_id` (UUID FK→tarea CASCADE), `autor_id` (UUID FK→usuario RESTRICT), `texto` (Text), `comentado_at` (DateTime tz default now).
  - `__table_args__` en `ComentarioTarea`: índice en `tarea_id`. **NO** declarar `ix_comentario_tarea_tenant_id`.
- [x] 1.2 Registrar `Tarea` y `ComentarioTarea` en `backend/app/models/__init__.py`.
- [x] 1.3 Crear `backend/alembic/versions/013_tareas_internas.py` (revision `013_tareas_internas`, down_revision `012_avisos_acknowledgment`):
  - Tablas `tarea` y `comentario_tarea` con FKs e índices del 1.1.
  - Seed idempotente: permiso `tareas:gestionar` por tenant; asignarlo a COORDINADOR, ADMIN, PROFESOR, TUTOR (patrón `ON CONFLICT DO NOTHING`).
  - `downgrade()`: drop tablas en orden inverso de FK + borrar permiso/asignaciones.

## 2. Schemas Pydantic (`extra='forbid'`)

- [x] 2.1 Crear `backend/app/schemas/tareas.py`:
  - `CrearTareaRequest`: `asignado_a` (UUID), `descripcion` (str, min_length=1), `materia_id` (UUID|None=None), `contexto_id` (UUID|None=None). Validar descripcion no vacía.
  - `CambiarEstadoRequest`: `estado` (Literal["Pendiente","En progreso","Resuelta","Cancelada"]).
  - `TareaResponse`: todos los campos de `Tarea` + `from_attributes=True`.
  - `CrearComentarioRequest`: `texto` (str, min_length=1).
  - `ComentarioResponse`: `id`, `tarea_id`, `autor_id`, `texto`, `comentado_at`, `from_attributes=True`.

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/tareas.py`:
  - `TareaRepository(TenantScopedRepository[Tarea])`: `create`, `get`, `list_mis_tareas(usuario_id, estado?, materia_id?)` (where asignado_a=uid OR asignado_por=uid), `list_admin(asignado_a?, asignado_por?, materia_id?, estado?, limit=50, offset=0)`.
  - `ComentarioTareaRepository(TenantScopedRepository[ComentarioTarea])`: `create`, `list_by_tarea(tarea_id)` (orden `comentado_at` ASC).

## 4. Service

- [x] 4.1 Crear `backend/app/services/tarea_service.py` con `TareaService(session, tenant_id)`:
  - `_resolve_usuario(auth_user_id)` → `usuario.id` via `UsuarioRepository.get_by_auth_user_id()`.
  - `_transicion_valida(estado_actual, estado_nuevo, actor_id, tarea)` → bool. Ver D1 en design.md.
- [x] 4.2 `crear_tarea(actor_id, payload, ip)`: crear `Tarea` (estado=`Pendiente`, `asignado_por`=actor resuelto) → audit `TAREA_CREAR` → 201.
- [x] 4.3 `cambiar_estado(actor_id, tarea_id, nuevo_estado, ip)`: validar existencia (404) → validar transición (422 si inválida) → update → audit `TAREA_ESTADO` con estado anterior y nuevo.
- [x] 4.4 `listar_mis_tareas(auth_user_id, estado?, materia_id?)`: resolver usuario → `list_mis_tareas`.
- [x] 4.5 `listar_admin(asignado_a?, asignado_por?, materia_id?, estado?, limit, offset)`: `list_admin` directo.
- [x] 4.6 `agregar_comentario(actor_id, tarea_id, texto, ip)`: validar tarea existe (404) → crear comentario → audit `TAREA_COMENTAR` → 201.
- [x] 4.7 `listar_comentarios(tarea_id)`: validar tarea existe (404) → `list_by_tarea`.

## 5. Router

- [x] 5.1 Crear `backend/app/api/v1/routers/tareas.py` con `router = APIRouter(prefix="/api/tareas", tags=["tareas"])`:
  - `POST /api/tareas` → `crear_tarea` (201), permiso `tareas:gestionar`.
  - `GET /api/tareas/mis-tareas` → `listar_mis_tareas`, permiso `tareas:gestionar`. (**Registrar ANTES de `/{id}`**.)
  - `GET /api/tareas` → `listar_admin`, permiso `tareas:gestionar` (COORD/ADMIN enforced en service).
  - `PATCH /api/tareas/{id}/estado` → `cambiar_estado`, permiso `tareas:gestionar`.
  - `POST /api/tareas/{id}/comentarios` → `agregar_comentario` (201), permiso `tareas:gestionar`.
  - `GET /api/tareas/{id}/comentarios` → `listar_comentarios`, permiso `tareas:gestionar`.
- [x] 5.2 Registrar `tareas_router` en `backend/app/main.py`.

## 6. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 6.1 Test crear tarea: crea `Tarea` con estado `Pendiente`; `asignado_por` = actor; sin permiso → 403; descripcion vacía → 422; campo extra → 422. Triangular: tarea con materia_id, tarea sin materia_id.
- [x] 6.2 Test máquina de estados: transiciones válidas (`Pendiente→En progreso`, `En progreso→Resuelta`); transición inválida (`Resuelta→En progreso`) → 422; cancelar por asignador; audit `TAREA_ESTADO` contiene estado anterior y nuevo.
- [x] 6.3 Test mis-tareas: usuario ve tareas donde es `asignado_a` o `asignado_por`; NO ve tareas de terceros; filtro por `estado`; filtro por `materia_id`.
- [x] 6.4 Test administración: COORDINADOR ve todas las tareas del tenant; filtros combinados (`asignado_a + estado`); aislamiento de tenant (tarea de otro tenant no aparece).
- [x] 6.5 Test comentarios: agregar comentario → 201 con audit `TAREA_COMENTAR`; listar comentarios en orden cronológico; texto vacío → 422; comentar en tarea de otro tenant → 404.
