# Proposal: C-16 — Tareas Internas

## Why

La coordinación académica depende actualmente de medios externos (WhatsApp, email) para asignar y hacer seguimiento de tareas entre docentes. Esto rompe la trazabilidad del equipo y hace imposible auditar quién asignó qué, cuándo y con qué resultado.

## What Changes

- Modelo `Tarea` con estados (`Pendiente → En progreso → Resuelta | Cancelada`), asignador, asignado, materia opcional y referencia de contexto libre.
- Modelo `ComentarioTarea` para el hilo de comentarios/evidencias asociado a cada tarea.
- API `/api/tareas/*` con tres modos de uso: vista personal (mis tareas), asignación/delegación entre docentes, y administración global con filtros (COORDINADOR/ADMIN).
- Permiso `tareas:gestionar` asignado por seed a COORDINADOR, ADMIN, PROFESOR y TUTOR.
- Migración `013_tareas_internas`: tablas `tarea` y `comentario_tarea`.
- Auditoría en acciones de creación (`TAREA_CREAR`), cambio de estado (`TAREA_ESTADO`) y comentario (`TAREA_COMENTAR`).

## Capabilities

### New Capabilities

- `tareas-internas`: Gestión de tareas internas asignadas entre roles del equipo docente y coordinación, con workflow de estado, hilo de comentarios y filtros de administración.

### Modified Capabilities

*(ninguna — este módulo es nuevo)*

## Impact

- **Nueva migración**: `013_tareas_internas` (revision `013_tareas_internas`, down_revision `012_avisos_acknowledgment`).
- **Nuevos modelos**: `Tarea`, `ComentarioTarea` (ambos con `TenantScopedMixin`).
- **Nuevos endpoints**: 7 rutas bajo `/api/tareas`.
- **Dependencia**: `C-07 usuarios-y-asignaciones` (FK a `usuario`), `C-06 estructura-academica` (FK a `materia`).
- **Alto uso**: el módulo gestiona cientos de tareas simultáneas; los índices en `asignado_a`, `asignado_por`, `materia_id` y `estado` son críticos.
