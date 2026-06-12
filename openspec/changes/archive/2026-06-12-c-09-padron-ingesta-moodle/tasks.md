## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/padron.py` con `VersionPadron` (id, tenant_id, materia_id, cohorte_id, cargado_por, cargado_at, activa) y `EntradaPadron` (id, version_id, tenant_id, usuario_id nullable, nombre, apellidos, email_encrypted, email_hash, comision, regional)
- [x] 1.2 Registrar ambos modelos en `backend/app/models/__init__.py`
- [x] 1.3 Crear migración `backend/alembic/versions/005_padron.py` con tablas `version_padron` y `entrada_padron`; índice único en `(tenant_id, materia_id, cohorte_id)` WHERE `activa=true` en `version_padron`

## 2. Schemas Pydantic

- [x] 2.1 Crear `backend/app/schemas/padron.py` con `extra='forbid'`: `CargarPadronResponse`, `EntradaPadronItem`, `PadronActivoResponse`, `DescartePadronResponse`
- [x] 2.2 Agregar schema `CargarMoodleRequest` con `materia_id`, `cohorte_id`, `moodle_course_id`

## 3. Integración Moodle WS

- [x] 3.1 Crear `backend/app/integrations/moodle_ws.py` con clase `MoodleWSClient(base_url, token)` usando `httpx.AsyncClient`
- [x] 3.2 Implementar `get_enrolled_users(course_id) -> list[dict]` que llama a `core_enrol_get_enrolled_users`; lanza `MoodleWSError` en error HTTP o respuesta de error Moodle
- [x] 3.3 Definir `MoodleWSError(Exception)` con `status_code` y `detail`

## 4. Parser de archivo

- [x] 4.1 Crear `backend/app/services/padron_parser.py` con `parse_file(content: bytes, filename: str) -> list[dict]`
- [x] 4.2 Soportar `.xlsx` via `openpyxl` y `.csv` via `csv.DictReader`; detectar columnas por nombre normalizado (case-insensitive, sin tildes)
- [x] 4.3 Mapear columnas: `Nombre` → `nombre`, `Apellido(s)` → `apellidos`, `Dirección de correo` → `email`, `Grupos` → `comision`
- [x] 4.4 Lanzar `ParseError(missing_columns: list[str])` si falta alguna columna obligatoria; lanzar `ParseError` si no hay filas de datos

## 5. Repository

- [x] 5.1 Crear `backend/app/repositories/padron.py` con `VersionPadronRepository(TenantScopedRepository)` con métodos: `get_activa(materia_id, cohorte_id)`, `desactivar_anterior(materia_id, cohorte_id)`, `create(version)`, `get_entradas(version_id)`
- [x] 5.2 Agregar `EntradaPadronRepository` con `bulk_create(entradas: list[EntradaPadron])`, `list_by_version(version_id)`

## 6. Service

- [x] 6.1 Crear `backend/app/services/padron_service.py` con `PadronService(session, tenant_id)`
- [x] 6.2 Implementar `cargar_desde_archivo(actor_id, materia_id, cohorte_id, content, filename, ip)`: parsear → desactivar anterior → crear VersionPadron activa → bulk_create EntradaPadron (con email_encrypted + email_hash) → audit `PADRON_CARGAR`
- [x] 6.3 Implementar `cargar_desde_moodle(actor_id, materia_id, cohorte_id, moodle_course_id, ip)`: obtener tenant para WS config → llamar `MoodleWSClient.get_enrolled_users` → misma lógica de activación → audit
- [x] 6.4 Implementar `get_padron_activo(materia_id, cohorte_id) -> PadronActivoResponse`: busca versión activa, lista entradas descifradas; retorna vacío si no hay versión
- [x] 6.5 Implementar `descartar_padron(actor_id, materia_id, cohorte_id, ip)`: desactiva versión activa → audit `PADRON_CARGAR` con `operacion: "descarte"` → lanza `NotFoundError` si no existe versión activa

## 7. Router

- [x] 7.1 Crear `backend/app/api/v1/routers/padron.py` con `router = APIRouter(prefix="/api/padron", tags=["padron"])`; registrar en `backend/app/main.py`
- [x] 7.2 `POST /api/padron/cargar` — requiere `padron:gestionar`; acepta `UploadFile` + `materia_id` + `cohorte_id`; llama `cargar_desde_archivo`; retorna 201 `CargarPadronResponse`
- [x] 7.3 `POST /api/padron/cargar-moodle` — requiere `padron:gestionar`; body `CargarMoodleRequest`; llama `cargar_desde_moodle`; retorna 201; maneja `MoodleWSError` → 502
- [x] 7.4 `GET /api/padron/activo` — requiere `padron:gestionar`; query params `materia_id`, `cohorte_id`; llama `get_padron_activo`; retorna 200
- [x] 7.5 `DELETE /api/padron/activo` — requiere `padron:gestionar`; query params `materia_id`, `cohorte_id`; llama `descartar_padron`; retorna 200; maneja `NotFoundError` → 404

## 8. Tests (Strict TDD — Red → Green → Triangulate → Refactor)

- [x] 8.1 Test parser: xlsx con columnas correctas carga N entradas; csv sin columna obligatoria lanza ParseError con columna listada; archivo vacío lanza ParseError
- [x] 8.2 Test `cargar_desde_archivo`: carga exitosa crea VersionPadron activa + N EntradaPadron; segunda carga desactiva la primera; audit_log registrado
- [x] 8.3 Test `GET /api/padron/activo`: devuelve entradas de versión activa; sin versión activa retorna vacío; tenant isolation (materia de otro tenant → 404)
- [x] 8.4 Test `POST /api/padron/cargar`: 201 con entradas_cargadas; columna faltante → 422; sin permiso → 403
- [x] 8.5 Test `DELETE /api/padron/activo`: descarte exitoso → 200 + entradas_descartadas; sin versión activa → 404
- [x] 8.6 Test Moodle WS: tenant sin config → 422; Moodle error → 502; carga exitosa → 201
