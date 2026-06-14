## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/encuentros.py` con `SlotEncuentro` (id, tenant_id, asignacion_id, materia_id, titulo, hora, dia_semana, fecha_inicio, cant_semanas, fecha_unica nullable, meet_url, vig_desde, vig_hasta), `InstanciaEncuentro` (id, tenant_id, slot_id nullable, materia_id, fecha, hora, titulo, estado, meet_url, video_url nullable, comentario) y `Guardia` (id, tenant_id, asignacion_id, materia_id, carrera_id, cohorte_id, dia, horario, estado, comentarios, creada_at). Todos heredan `TenantScopedMixin`.
- [x] 1.2 Registrar los tres modelos en `backend/app/models/__init__.py`
- [x] 1.3 Crear migración `backend/alembic/versions/010_encuentros_guardias.py` (revision `010_encuentros_guardias`, down_revision `009_comunicaciones`) con tablas `slot_encuentro`, `instancia_encuentro` (FK `slot_id` → `slot_encuentro.id` `ondelete=SET NULL`), `guardia`; índices por `tenant_id`, `materia_id` y `slot_id`

## 2. Schemas Pydantic (`extra='forbid'`)

- [x] 2.1 Crear `backend/app/schemas/encuentros.py`: `CrearRecurrenteRequest` (materia_id, asignacion_id, dia_semana, hora, fecha_inicio, cant_semanas 1..52, titulo, meet_url, validator dia_semana == fecha_inicio.weekday()), `CrearUnicoRequest` (materia_id, asignacion_id, fecha, hora, titulo, meet_url), `EditarInstanciaRequest` (estado?, meet_url?, video_url?, comentario? — solo estos 4), `InstanciaEncuentroResponse`, `SlotEncuentroResponse`, `BloqueHtmlResponse` (html: str)
- [x] 2.2 Crear `backend/app/schemas/guardias.py`: `RegistrarGuardiaRequest` (asignacion_id, materia_id, carrera_id, cohorte_id, dia, horario, comentarios?), `GuardiaResponse`

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/encuentros.py` con `SlotEncuentroRepository(TenantScopedRepository)` (`create`, `get`), `InstanciaEncuentroRepository(TenantScopedRepository)` (`bulk_create(instancias)`, `list(materia_id?, cohorte_id?, estado?, desde?, hasta?)`, `list_by_materia(materia_id)` ordenado por fecha, `get`, `update`)
- [x] 3.2 Agregar `GuardiaRepository(TenantScopedRepository)` con `create`, `list(materia_id?, carrera_id?, cohorte_id?, estado?)`

## 4. Service de encuentros

- [x] 4.1 Crear `backend/app/services/encuentro_service.py` con `EncuentroService(session, tenant_id)`
- [x] 4.2 Implementar `crear_recurrente(actor_id, payload, ip)`: validar asignación pertenece al tenant → crear `SlotEncuentro` (cant_semanas=N) → generar N `InstanciaEncuentro` en `Programado` con fecha `fecha_inicio + timedelta(weeks=k)` → audit `ENCUENTRO_GESTIONAR` con `filas_afectadas=N` → commit atómico
- [x] 4.3 Implementar `crear_unico(actor_id, payload, ip)`: crear `SlotEncuentro` (cant_semanas=0, fecha_unica=fecha, fecha_inicio=fecha) + una `InstanciaEncuentro` → audit
- [x] 4.4 Implementar `editar_instancia(instancia_id, payload)`: aplicar solo estado/meet_url/video_url/comentario; `NotFoundError` si no existe en el tenant
- [x] 4.5 Implementar `listar_encuentros(materia_id?, cohorte_id?, estado?, desde?, hasta?)` → todas las instancias del tenant (vista admin)
- [x] 4.6 Implementar `generar_bloque_html(materia_id, cohorte_id?)`: instancias ordenadas por fecha → tabla HTML con título/fecha/hora/meet_url/video_url, escapando con `html.escape`; devuelve string (vacío sin filas si no hay instancias)

## 5. Service de guardias

- [x] 5.1 Crear `backend/app/services/guardia_service.py` con `GuardiaService(session, tenant_id)`
- [x] 5.2 Implementar `registrar(actor_id, payload, ip)`: validar `asignacion_id` pertenece al tenant (`NotFoundError` si no) → crear `Guardia` en `Pendiente` → audit `GUARDIA_REGISTRAR` → commit
- [x] 5.3 Implementar `listar(materia_id?, carrera_id?, cohorte_id?, estado?)`
- [x] 5.4 Implementar `exportar(filtros)` → CSV (usuario_id, materia, carrera, cohorte, dia, horario, estado, comentarios), patrón de `equipo_service.exportar_equipo`

## 6. Routers

- [x] 6.1 Crear `backend/app/api/v1/routers/encuentros.py` con `router = APIRouter(prefix="/api/encuentros", tags=["encuentros"])`, guard `require_permission("encuentros:gestionar")`; registrar en `backend/app/main.py`
- [x] 6.2 `POST /api/encuentros/recurrente` → 201; `POST /api/encuentros/unico` → 201; `PATCH /api/encuentros/instancias/{id}` (NotFoundError → 404); `GET /api/encuentros` (vista admin con filtros); `GET /api/encuentros/bloque-html` → BloqueHtmlResponse
- [x] 6.3 Crear `backend/app/api/v1/routers/guardias.py` con `prefix="/api/guardias"`, guard `require_permission("guardias:registrar")`; registrar en `backend/app/main.py`
- [x] 6.4 `POST /api/guardias` → 201 (asignación de otro tenant → 404); `GET /api/guardias` (filtros); `GET /api/guardias/exportar` → StreamingResponse CSV

## 7. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 7.1 Test generación recurrente: `cant_semanas=8` crea slot + 8 instancias en `Programado` con fechas a +7 días (triangular: cant_semanas=1 → 1 instancia); `fecha_inicio` incoherente con `dia_semana` → 422; sin permiso → 403; audit_log con filas_afectadas=8
- [x] 7.2 Test encuentro único: crea slot (cant_semanas=0) + 1 instancia en la fecha indicada
- [x] 7.3 Test editar instancia: `estado=Realizado` + `video_url` persiste; `estado=Cancelado` persiste; campo extra (`fecha`) → 422; id inexistente → 404
- [x] 7.4 Test bloque HTML: con instancias devuelve HTML con filas y links escapados; sin instancias devuelve bloque vacío + 200
- [x] 7.5 Test vista admin `GET /api/encuentros`: devuelve instancias de otros docentes del tenant; filtro `estado=Realizado` acota; tenant isolation (materia de otro tenant no aparece)
- [x] 7.6 Test registrar guardia: 201 en `Pendiente` + audit `GUARDIA_REGISTRAR`; `asignacion_id` de otro tenant → 404; sin permiso → 403
- [x] 7.7 Test consulta/export guardias: filtro por materia acota; export devuelve CSV con headers + filas; sin guardias → CSV solo headers + 200
