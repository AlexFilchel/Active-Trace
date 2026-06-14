# Tasks: C-17 — Programas y Fechas Académicas

> Strict TDD por tarea de test: Safety Net → RED → GREEN → TRIANGULATE → REFACTOR. No mockear la DB.
> Permiso `estructura:gestionar` ya existe — no seedear de nuevo.

## 0. Safety Net

- [x] 0.1 Correr suite existente y capturar baseline. Si algo falla, reportar como pre-existing, no arreglar.

## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/programas.py` con `ProgramaMateria` y `FechaAcademica` (ambos heredan `TenantScopedMixin`):
  - `ProgramaMateria`: `materia_id` (UUID FK→materia RESTRICT), `carrera_id` (UUID FK→carrera RESTRICT), `cohorte_id` (UUID FK→cohorte RESTRICT), `titulo` (String 255), `referencia_archivo` (Text), `cargado_at` (DateTime tz default now).
  - `__table_args__` en `ProgramaMateria`: índices en `materia_id`, `carrera_id`, `cohorte_id`. **NO** declarar `ix_programa_materia_tenant_id` (lo crea el mixin).
  - `FechaAcademica`: `materia_id` (UUID FK→materia RESTRICT), `cohorte_id` (UUID FK→cohorte RESTRICT), `tipo` (String 20, enum: Parcial/TP/Coloquio/Recuperatorio), `numero` (Integer), `periodo` (String 20), `fecha` (Date), `titulo` (String 255).
  - `__table_args__` en `FechaAcademica`: índices en `materia_id`, `cohorte_id`, `tipo`. **NO** declarar `ix_fecha_academica_tenant_id`.
- [x] 1.2 Registrar `ProgramaMateria` y `FechaAcademica` en `backend/app/models/__init__.py`.
- [x] 1.3 Crear `backend/alembic/versions/014_programas_fechas_academicas.py` (revision `014_programas_fechas_academicas`, down_revision `013_tareas_internas`):
  - Tablas `programa_materia` y `fecha_academica` con FKs e índices del 1.1.
  - Sin seed de permisos (reutiliza `estructura:gestionar` de C-06).
  - `downgrade()`: drop tablas en orden inverso.

## 2. Schemas Pydantic (`extra='forbid'`)

- [x] 2.1 Crear `backend/app/schemas/programas.py`:
  - `CrearProgramaRequest`: `materia_id` (UUID), `carrera_id` (UUID), `cohorte_id` (UUID), `titulo` (str min_length=1 max_length=255), `referencia_archivo` (str min_length=1).
  - `ProgramaResponse`: todos los campos de `ProgramaMateria` + `from_attributes=True`.
  - `CrearFechaAcademicaRequest`: `materia_id` (UUID), `cohorte_id` (UUID), `tipo` (Literal[...]), `numero` (int ge=1), `periodo` (str min_length=1), `fecha` (date), `titulo` (str min_length=1 max_length=255).
  - `EditarFechaAcademicaRequest`: todos los campos opcionales (None por defecto), mismas validaciones.
  - `FechaAcademicaResponse`: todos los campos + `from_attributes=True`.
  - `FragmentoLmsResponse`: `texto` (str).

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/programas.py`:
  - `ProgramaRepository(TenantScopedRepository[ProgramaMateria])`: `create`, `get`, `list_filtrado(materia_id?, carrera_id?, cohorte_id?)`.
  - `FechaAcademicaRepository(TenantScopedRepository[FechaAcademica])`: `create`, `get`, `update`, `list_filtrado(materia_id?, cohorte_id?, tipo?, periodo?)` ordenado por `fecha` ASC.

## 4. Service

- [x] 4.1 Crear `backend/app/services/programa_service.py` con `ProgramaService(session, tenant_id)`:
  - `crear_programa(actor_id, payload, ip)` → audit `PROGRAMA_CREAR` → 201.
  - `listar_programas(materia_id?, carrera_id?, cohorte_id?)` → lista filtrada.
  - `crear_fecha(actor_id, payload, ip)` → audit `FECHA_ACAT_CREAR` → 201.
  - `editar_fecha(actor_id, fecha_id, payload, ip)` → validar existencia (404) → audit `FECHA_ACAT_EDITAR` → 200.
  - `listar_fechas(materia_id?, cohorte_id?, tipo?, periodo?)` → lista ordenada ASC.
  - `generar_fragmento_lms(materia_id, cohorte_id, periodo)` → texto formateado con todas las fechas del período.

## 5. Router

- [x] 5.1 Crear `backend/app/api/v1/routers/programas.py` con dos routers:
  - `programas_router = APIRouter(prefix="/api/programas", tags=["programas"])`:
    - `POST /api/programas` → `crear_programa` (201), permiso `estructura:gestionar`.
    - `GET /api/programas` → `listar_programas`, permiso `estructura:gestionar`.
  - `fechas_router = APIRouter(prefix="/api/fechas-academicas", tags=["fechas-academicas"])`:
    - `GET /api/fechas-academicas/fragmento-lms` → `generar_fragmento_lms`. (**BEFORE `/{id}`**.)
    - `POST /api/fechas-academicas` → `crear_fecha` (201), permiso `estructura:gestionar`.
    - `GET /api/fechas-academicas` → `listar_fechas`, permiso `estructura:gestionar`.
    - `PATCH /api/fechas-academicas/{id}` → `editar_fecha`, permiso `estructura:gestionar`.
- [x] 5.2 Registrar `programas_router` y `fechas_router` en `backend/app/main.py`.

## 6. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 6.1 Test programas CRUD: crear programa válido → 201 + audit `PROGRAMA_CREAR`; sin permiso → 403; campo obligatorio ausente → 422; campo extra → 422. Triangular: listar con filtro materia_id + cohorte_id; aislamiento de tenant.
- [x] 6.2 Test fechas CRUD: crear fecha válida → 201 + audit `FECHA_ACAT_CREAR`; tipo inválido → 422; numero ≤ 0 → 422; editar fecha → 200 + audit `FECHA_ACAT_EDITAR`; editar fecha de otro tenant → 404. Triangular: listar filtrado por tipo + periodo.
- [x] 6.3 Test fragmento LMS: con fechas → retorna texto no vacío con formato; sin fechas → retorna `{ "texto": "" }`; aislamiento de tenant en fragmento.
