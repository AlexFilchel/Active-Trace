# Tasks: C-14 Evaluaciones y Coloquios

> Strict TDD por tarea de test: Safety Net (correr tests del/los archivos a tocar) → RED (test que falla) → GREEN (código mínimo) → TRIANGULATE (2do caso, edge) → REFACTOR (tests verdes tras cada paso). No mockear la DB.

## 0. Safety Net

- [x] 0.1 Correr la suite de modelos/migraciones existente y capturar baseline ("N passing"). Si algo falla, reportar como pre-existing, no arreglar.

## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/evaluaciones.py` con (todos heredan `TenantScopedMixin`):
  - `Evaluacion` (materia_id, cohorte_id, tipo `Coloquio` default, instancia, dias_disponibles int, estado `Abierta` default)
  - `DiaEvaluacion` (evaluacion_id, fecha, cupo_total)
  - `CandidatoEvaluacion` (evaluacion_id, alumno_id)
  - `ReservaEvaluacion` (evaluacion_id, dia_evaluacion_id, alumno_id index=True, fecha_hora, estado `Activa` default)
  - `ResultadoEvaluacion` (evaluacion_id, alumno_id, nota_final str)
- [x] 1.2 `__table_args__`: índices SOLO para columnas no autoindexadas — `ix_evaluacion_materia_id`, `ix_evaluacion_cohorte_id`, `ix_dia_evaluacion_evaluacion_id`, `ix_candidato_evaluacion_evaluacion_id`, `ix_reserva_evaluacion_evaluacion_id`, `ix_reserva_evaluacion_dia_id`, `ix_resultado_evaluacion_evaluacion_id`. **NO** declarar `ix_<tabla>_tenant_id` (lo crea el mixin → duplicado rompe `ensure_schema()`).
- [x] 1.3 Registrar los 5 modelos en `backend/app/models/__init__.py` (import + `__all__`)
- [x] 1.4 Crear migración `backend/alembic/versions/011_evaluaciones_coloquios.py` (revision `011_evaluaciones_coloquios`, down_revision `010_encuentros_guardias`): tablas `evaluacion`, `dia_evaluacion` (FK evaluacion_id CASCADE), `candidato_evaluacion` (FK evaluacion_id CASCADE, alumno_id RESTRICT), `reserva_evaluacion` (FK evaluacion_id/dia_evaluacion_id RESTRICT, alumno_id RESTRICT), `resultado_evaluacion`; índices del 1.2; índice único parcial sobre reservas activas `(tenant_id, evaluacion_id, alumno_id) WHERE deleted_at IS NULL AND estado = 'Activa'`.
- [x] 1.5 En la misma migración, seed idempotente (patrón de `009_comunicaciones.py`): insertar permiso `coloquios:gestionar` por tenant (`ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING`) y asignarlo a roles `COORDINADOR` y `ADMIN` (`ON CONFLICT ON CONSTRAINT uq_rol_permiso_rol_permiso DO NOTHING`). `downgrade()` borra tablas en orden inverso de FK + el permiso/asignaciones agregadas.

## 2. Schemas Pydantic (`extra='forbid'`)

- [x] 2.1 Crear `backend/app/schemas/coloquios.py`:
  - `DiaConvocatoriaIn` (fecha, cupo_total > 0)
  - `CrearConvocatoriaRequest` (materia_id, cohorte_id, instancia, dias: list[DiaConvocatoriaIn] no vacía)
  - `EditarConvocatoriaRequest` (instancia?, estado? `Abierta|Cerrada`)
  - `ImportarCandidatosRequest` (alumno_ids: list[UUID])
  - `ReservarTurnoRequest` (dia_evaluacion_id) — **sin** alumno_id (se toma de sesión)
  - `CancelarReservaRequest` (estado = `Cancelada`)
  - `RegistrarResultadoRequest` (alumno_id, nota_final)
  - Responses: `ConvocatoriaResponse` (+ métricas convocados/reservas_activas/cupos_libres), `ReservaResponse`, `ResultadoResponse`, `MetricasResponse`, `AgendaDiaResponse`

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/coloquios.py` con (todos `TenantScopedRepository`):
  - `EvaluacionRepository`: `create`, `get`, `list`, `update`
  - `DiaEvaluacionRepository`: `bulk_create`, `list_by_evaluacion`, `get_for_update(dia_id)` (con `with_for_update()`)
  - `CandidatoEvaluacionRepository`: `upsert_many(evaluacion_id, alumno_ids)` idempotente, `es_candidato(evaluacion_id, alumno_id)`, `count_by_evaluacion`
  - `ReservaEvaluacionRepository`: `create`, `get`, `count_activas_por_dia(dia_id)`, `tiene_reserva_activa(evaluacion_id, alumno_id)`, `list_activas_por_evaluacion`, `update`, `count_activas_tenant`
  - `ResultadoEvaluacionRepository`: `upsert(evaluacion_id, alumno_id, nota_final)`, `list_by_evaluacion`, `count_tenant`

## 4. Service de coloquios

- [x] 4.1 Crear `backend/app/services/coloquio_service.py` con `ColoquioService(session, tenant_id)`
- [x] 4.2 `crear_convocatoria(actor_id, payload, ip)`: crear `Evaluacion` Abierta → N `DiaEvaluacion` → audit `COLOQUIO_CREAR` (`filas_afectadas=N`) → commit atómico
- [x] 4.3 `importar_candidatos(actor_id, evaluacion_id, alumno_ids, ip)`: validar convocatoria del tenant (`NotFoundError`→404) → upsert idempotente → audit `COLOQUIO_IMPORTAR_CANDIDATOS`
- [x] 4.4 `reservar(actor_id_alumno, evaluacion_id, dia_evaluacion_id, ip)`: validar convocatoria Abierta (cerrada→409); validar `es_candidato` (no→403); `get_for_update(dia)`; si `count_activas_por_dia >= cupo_total`→`SinCupoError` 409; si `tiene_reserva_activa`→`ReservaDuplicadaError` 409; crear `ReservaEvaluacion` Activa → audit `COLOQUIO_RESERVAR` → commit
- [x] 4.5 `cancelar_reserva(actor_id_alumno, reserva_id)`: validar pertenece al alumno de sesión (no→404) → estado `Cancelada` → audit `COLOQUIO_CANCELAR_RESERVA`
- [x] 4.6 `listar_convocatorias()`: convocatorias del tenant con métricas derivadas (convocados, reservas_activas, cupos_libres)
- [x] 4.7 `metricas()`: agregados del tenant (convocados, instancias_activas, reservas_activas, notas_registradas)
- [x] 4.8 `editar_convocatoria(evaluacion_id, payload)` y cierre (estado `Cerrada`); `agenda(evaluacion_id)` → reservas activas agrupadas por día
- [x] 4.9 `registrar_resultado(actor_id, evaluacion_id, alumno_id, nota_final, ip)` upsert; `listar_resultados(evaluacion_id)`

## 5. Routers

- [x] 5.1 Crear `backend/app/api/v1/routers/coloquios.py` con `router = APIRouter(prefix="/api/coloquios", tags=["coloquios"])`; registrar en `backend/app/main.py`
- [x] 5.2 Endpoints de gestión con `require_permission("coloquios:gestionar")`: `POST /api/coloquios` (201), `GET /api/coloquios`, `GET /api/coloquios/metricas`, `PATCH /api/coloquios/{id}`, `POST /api/coloquios/{id}/candidatos`, `GET /api/coloquios/{id}/agenda`, `POST /api/coloquios/{id}/resultados`, `GET /api/coloquios/{id}/resultados` (NotFoundError→404)
- [x] 5.3 Endpoints de reserva con `require_permission("evaluacion:reservar_instancia")`: `POST /api/coloquios/{id}/reservas` (201; alumno_id desde sesión), `PATCH /api/coloquios/reservas/{id}` (cancelar)

## 6. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 6.1 Test crear convocatoria: 2 días → 1 `Evaluacion` Abierta + 2 `DiaEvaluacion` con cupos; audit `COLOQUIO_CREAR` filas_afectadas=2 (triangular: 1 día → 1 `DiaEvaluacion`); `cupo_total<=0`→422; campo extra→422; sin permiso→403
- [x] 6.2 Test importar candidatos: registra 1 `CandidatoEvaluacion` por alumno; reimportar mismo alumno no duplica (200); convocatoria de otro tenant→404
- [x] 6.3 Test reservar con cupo: crea `ReservaEvaluacion` Activa para alumno de sesión + cupo libre baja en 1; audit `COLOQUIO_RESERVAR` (triangular: 2da reserva de otro alumno baja cupo a N-2)
- [x] 6.4 Test sin cupo rechaza: día con reservas activas == cupo_total → 409, no crea reserva
- [x] 6.5 Test reglas de reserva: alumno no candidato→403; reserva duplicada del mismo alumno→409; reserva en convocatoria Cerrada→409; alumno_id de payload distinto al de sesión es ignorado/422 (identidad desde sesión)
- [x] 6.6 Test cancelar libera cupo: cancelar reserva activa → estado `Cancelada` + cupo libre sube en 1 (permite re-reservar); cancelar reserva ajena→404
- [x] 6.7 Test listado/métricas: `GET /api/coloquios` devuelve convocados/reservas_activas/cupos_libres derivados; tenant aislado (convocatoria de otro tenant no aparece); `GET /api/coloquios/metricas` agrega convocados/instancias_activas/reservas_activas/notas_registradas
- [x] 6.8 Test resultados: registrar `ResultadoEvaluacion`; reregistrar mismo alumno actualiza nota sin duplicar; `GET /api/coloquios/{id}/resultados` lista por convocatoria; agenda `GET /api/coloquios/{id}/agenda` agrupa reservas activas por día
