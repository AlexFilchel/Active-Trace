## 1. Migración y modelos

- [x] 1.1 Crear `alembic/versions/007_calificaciones.py`: tablas `calificacion` y `umbral_materia`, unique constraint en `(tenant_id, entrada_padron_id, actividad, actor_id)` para upsert, unique constraint en `(tenant_id, asignacion_id, materia_id)` para umbral; upgrade + downgrade
- [x] 1.2 Crear `app/models/calificacion.py`: modelo `Calificacion` (id UUID PK, tenant_id FK, entrada_padron_id FK, actor_id FK usuario, actividad str, nota_numerica Numeric nullable, nota_textual str nullable, aprobado bool, origen enum Importado, created_at, deleted_at soft-delete)
- [x] 1.3 Crear `app/models/umbral_materia.py`: modelo `UmbralMateria` (id UUID PK, tenant_id FK, asignacion_id FK, materia_id FK, umbral_pct Numeric default 60, valores_aprobatorios ARRAY[str] default ["Satisfactorio","Supera lo esperado"], created_at, updated_at)
- [x] 1.4 Registrar ambos modelos en `app/models/__init__.py` y en `ensure_schema()`

## 2. Parser LMS

- [x] 2.1 Crear `app/calificaciones/lms_parser.py`: función `detectar_actividades(archivo: bytes, extension: str) -> dict` que retorna `{actividades_numericas: [], actividades_textuales: []}`. Columnas `(Real)` → numéricas; columnas con valores del conjunto textual → textuales. No persiste nada.
- [x] 2.2 Crear `app/calificaciones/lms_parser.py` (cont.): función `extraer_calificaciones(archivo: bytes, extension: str, actividades_seleccionadas: list[str]) -> list[dict]` para el import definitivo (alumno_legajo, actividad, nota_numerica, nota_textual)
- [x] 2.3 Tests TDD para `lms_parser.py`: detectar columnas `(Real)`, detectar columnas textuales, columnas mixtas, archivo sin actividades válidas (≥2 casos por behavior)

## 3. Repository

- [x] 3.1 Crear `app/calificaciones/repository.py`: método `upsert_bulk(tenant_id, calificaciones: list[Calificacion])` usando `INSERT ... ON CONFLICT DO UPDATE`
- [x] 3.2 Agregar a repository: método `delete_by_actor_materia(tenant_id, actor_id, materia_id) -> int` (soft-delete o DELETE físico scope-isolated; retorna cantidad eliminada)
- [x] 3.3 Agregar a repository: método `get_sin_calificar_textual(tenant_id, asignacion_id, materia_id) -> list[dict]` para el reporte de finalización (cruza `entrada_padron` con `calificacion` donde no existe nota textual)
- [x] 3.4 Crear `app/calificaciones/umbral_repository.py`: métodos `get_by_asignacion(tenant_id, asignacion_id, materia_id) -> UmbralMateria | None` y `upsert(tenant_id, umbral: UmbralMateria) -> UmbralMateria`

## 4. Schemas Pydantic

- [x] 4.1 Crear `app/calificaciones/schemas.py`: `PreviewResponse` (actividades_numericas, actividades_textuales), `ImportRequest` (materia_id, actividades_seleccionadas, archivo base64 o multipart), `ImportResponse` (calificaciones_importadas: int), `VaciadoResponse` (eliminadas: int)
- [x] 4.2 Agregar schemas de umbral: `UmbralRequest` (umbral_pct, valores_aprobatorios), `UmbralResponse` (umbral_pct, valores_aprobatorios, es_defecto: bool). Todos con `extra='forbid'`

## 5. Service

- [x] 5.1 Crear `app/calificaciones/service.py`: método `preview(tenant_id, actor_id, archivo) -> PreviewResponse` — stateless, solo parseo
- [x] 5.2 Agregar a service: método `importar(tenant_id, actor_id, materia_id, actividades, archivo) -> ImportResponse`. Resuelve `asignacion_id` del actor, obtiene umbral vigente, deriva `aprobado` para cada fila, llama `upsert_bulk`, registra audit `CALIFICACIONES_IMPORTAR`
- [x] 5.3 Agregar a service: método `reporte_finalizacion(tenant_id, actor_id, materia_id, archivo) -> list[dict]` — stateless, cruza reporte con calificaciones textuales existentes
- [x] 5.4 Agregar a service: `vaciar(tenant_id, actor_id, materia_id) -> VaciadoResponse` — scope-isolated delete + audit `CALIFICACIONES_IMPORTAR` con `operacion=vaciado`
- [x] 5.5 Crear `app/calificaciones/umbral_service.py`: `get_umbral(tenant_id, actor_id, materia_id) -> UmbralResponse` (devuelve defecto si no existe) + `set_umbral(tenant_id, actor_id, materia_id, request) -> UmbralResponse`

## 6. Router y RBAC

- [x] 6.1 Crear `app/calificaciones/router.py`: `POST /api/calificaciones/preview`, `POST /api/calificaciones/importar`, `POST /api/calificaciones/reporte-finalizacion`, `DELETE /api/calificaciones`, `GET /api/calificaciones/umbral`, `PUT /api/calificaciones/umbral`. Todos requieren `require_permission("calificaciones:importar")`
- [x] 6.2 Registrar el router en `app/main.py`
- [x] 6.3 Agregar permiso `calificaciones:importar` al seed de RBAC para rol PROFESOR

## 7. Tests de integración TDD

- [x] 7.1 Crear `tests/test_calificaciones_migration_tdd.py`: verificar que `007_calificaciones` crea `calificacion` y `umbral_materia`, que el downgrade las elimina, sin afectar tablas previas
- [x] 7.2 Crear `tests/test_calificaciones_import_tdd.py`: preview detecta columnas correctamente, import crea N registros con `aprobado` correcto (numérico y textual), upsert sobreescribe, audit registrada, tenant isolation
- [x] 7.3 Agregar a tests: vaciado elimina solo registros del actor (no del otro docente), retorna 0 cuando no hay calificaciones
- [x] 7.4 Crear `tests/test_umbral_tdd.py`: GET retorna defecto cuando no existe, PUT persiste, cambio de umbral de docente A no afecta docente B
- [x] 7.5 Agregar drops de `calificacion` y `umbral_materia` a las funciones `reset_*` en los 5 archivos de migration-tests existentes (misma corrección que C-09 aplicó para `version_padron`/`entrada_padron`)

## 8. Actualizar CHANGES.md

- [x] 8.1 Marcar `[x] C-10` como archivado en `CHANGES.md` una vez completadas todas las tasks anteriores
