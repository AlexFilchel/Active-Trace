## Why

Con usuarios y asignaciones implementados (C-07), el sistema sabe qué docente está asignado a qué materia, pero no ofrece ninguna herramienta para planificar y registrar los encuentros sincrónicos (clases virtuales) ni para llevar el registro de guardias de atención a alumnos. Hoy esa coordinación ocurre fuera del sistema (planillas, mensajes sueltos), sin trazabilidad ni vista de supervisión. La Épica 6 (F6.1–F6.6) cierra ese vacío: permite crear encuentros recurrentes o únicos, registrar su realización y grabación, generar el bloque para embeber en el aula virtual del LMS, supervisar globalmente desde coordinación y registrar las guardias cubiertas por tutores.

## What Changes

- **Modelos nuevos**: `SlotEncuentro` (plantilla de recurrencia), `InstanciaEncuentro` (encuentro concreto, derivado de un slot o independiente) y `Guardia` (registro de atención).
- **Crear encuentro recurrente** (F6.1, RN-13): al crear un slot con `dia_semana`, `hora`, `fecha_inicio` y `cant_semanas`, el sistema genera automáticamente las N instancias en estado `Programado`.
- **Crear encuentro único** (F6.2): instancia puntual sin recurrencia (slot con `cant_semanas = 0` y `fecha_unica`).
- **Editar instancia** (F6.3): modificar `estado` (Programado/Realizado/Cancelado), `meet_url`, `video_url` y `comentario`.
- **Generar bloque HTML para el aula virtual** (F6.4): fragmento formateado con el calendario de encuentros y sus grabaciones, listo para copiar al LMS.
- **Vista admin de encuentros** (F6.5): listado transversal de todos los encuentros del tenant (COORDINADOR/ADMIN), más allá del docente que los creó.
- **Registro de guardias** (F6.6): el TUTOR registra su guardia; COORDINADOR/ADMIN consultan el registro filtrado global y lo exportan.
- **Endpoints** `/api/encuentros/*` y `/api/guardias/*` con guards de permiso fail-closed.
- **Migración `010_encuentros_guardias`**: tablas `slot_encuentro`, `instancia_encuentro`, `guardia`.
- **Auditoría**: las operaciones que crean/modifican encuentros y guardias registran en `AuditLog`.

## Capabilities

### New Capabilities

- `encuentros-y-guardias`: gestión de encuentros sincrónicos (slots recurrentes, instancias, edición de estado/grabación, bloque HTML para el LMS, vista admin global) y registro de guardias de atención (alta por tutor, consulta global y exportación por coordinación).

### Modified Capabilities

- Ninguna. El change construye sobre `usuarios-y-asignaciones` (C-07) sin modificar su spec: solo referencia `Asignacion` y `Materia` como contexto.

## Impact

- **Modelos nuevos**: `app/models/encuentros.py` — `SlotEncuentro`, `InstanciaEncuentro`, `Guardia`; registrados en `app/models/__init__.py`.
- **Migración nueva**: `app/alembic/versions/010_encuentros_guardias.py` (down_revision `009_comunicaciones`) — tablas `slot_encuentro`, `instancia_encuentro`, `guardia`.
- **Repositories nuevos**: `app/repositories/encuentros.py` — `SlotEncuentroRepository`, `InstanciaEncuentroRepository`, `GuardiaRepository` (todos `TenantScopedRepository`).
- **Services nuevos**: `app/services/encuentro_service.py` (generación de instancias, edición, bloque HTML) y `app/services/guardia_service.py` (registro, consulta, export).
- **Schemas nuevos**: `app/schemas/encuentros.py` y `app/schemas/guardias.py` — requests/responses con `extra='forbid'`.
- **Routers nuevos**: `app/api/v1/routers/encuentros.py` (`/api/encuentros/*`) y `app/api/v1/routers/guardias.py` (`/api/guardias/*`); registrados en `app/main.py`.
- **Permisos** (ya seedeados en `003_rbac.py`): `encuentros:gestionar` (TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN) y `guardias:registrar` (TUTOR, PROFESOR, COORDINADOR, ADMIN). No se crean permisos nuevos.
- **Auditoría**: integra `audit_action` (C-05) con códigos `ENCUENTRO_GESTIONAR` y `GUARDIA_REGISTRAR`.
- **Frontend**: fuera de scope (lo cubre la fase frontend).
