# Design: C-16 — Tareas Internas

## Context

El módulo de tareas internas es un sistema de coordinación asincrónica entre roles del equipo docente. La KB define el modelo en E12 (Tarea + ComentarioTarea) y el workflow en FL-05. El módulo es de **alto uso** (cientos de tareas simultáneas por período activo), lo que exige índices apropiados y queries eficientes.

Dependencias directas: `C-07 usuarios-y-asignaciones` (FK a `usuario`) y `C-06 estructura-academica` (FK a `materia`). Ambos están archivados.

## Goals / Non-Goals

**Goals:**
- CRUD de tareas con máquina de estados `Pendiente → En progreso → Resuelta | Cancelada`.
- Hilo de comentarios append-only por tarea.
- Vista personal (`mis-tareas`: asignado_a o asignado_por) y vista de administración global con filtros.
- Auditoría en crear, cambiar estado y comentar.
- Seed de permiso `tareas:gestionar` para COORDINADOR, ADMIN, PROFESOR, TUTOR.

**Non-Goals:**
- Notificaciones push o email al asignar una tarea (depende de C-11 comunicaciones).
- Subtareas o dependencias entre tareas.
- Adjuntos o archivos asociados a tareas.
- SLA o vencimiento automático de tareas.

## Decisions

### D1 — Máquina de estados explícita en el servicio
**Decisión**: La validación de transiciones vive en `TareaService`, no en el router ni en el modelo.

**Transiciones válidas**:
```
Pendiente     → En progreso  (asignado_a o asignador o COORD/ADMIN)
Pendiente     → Cancelada    (asignador o COORD/ADMIN)
En progreso   → Resuelta     (asignado_a o asignador o COORD/ADMIN)
En progreso   → Cancelada    (asignador o COORD/ADMIN)
Resuelta      → (terminal — no hay transiciones salientes)
Cancelada     → (terminal — no hay transiciones salientes)
```

**Alternativa descartada**: enum check solo en la DB (menos expresivo en errores 422).

### D2 — Un endpoint para mis-tareas, otro para administración global
**Decisión**: `GET /api/tareas/mis-tareas` (cualquier rol con permiso) y `GET /api/tareas` (COORD/ADMIN). Registrar `/mis-tareas` ANTES que `/{id}` en el router para evitar conflicto de rutas.

**Alternativa descartada**: un solo endpoint con flag `?modo=admin` (acoplamiento de roles en el query param, más difícil de testear).

### D3 — Comentarios append-only, sin editar ni borrar
**Decisión**: `POST /api/tareas/{id}/comentarios` y `GET /api/tareas/{id}/comentarios`. No hay `PATCH` ni `DELETE` en comentarios.

**Rationale**: auditoría y trazabilidad — un comentario registrado no puede borrarse, siguiendo el principio append-only de la plataforma.

### D4 — `contexto_id` como UUID libre sin FK enforced
**Decisión**: `contexto_id` es un UUID opcional sin foreign key definida en la DB — permite referenciar cualquier entidad del dominio (comunicacion, evaluacion, etc.) sin acoplamiento estructural.

**Trade-off**: no hay integridad referencial en la DB para este campo; la aplicación es responsable de validar si se necesita.

### D5 — Índices para alto uso
Índices en:
- `ix_tarea_tenant_id` (del mixin)
- `ix_tarea_asignado_a`
- `ix_tarea_asignado_por`
- `ix_tarea_materia_id`
- `ix_tarea_estado`
- `ix_comentario_tarea_tarea_id`

Los filtros combinados en administración son todos sobre estas columnas.

### D6 — Permiso único `tareas:gestionar` para todos los roles activos
**Decisión**: Un solo permiso cubre crear, ver, comentar y cambiar estado. La restricción de qué acciones puede hacer cada rol (ej: solo el asignador puede cancelar) se implementa en el service, no en el sistema de permisos.

**Alternativa descartada**: permisos `tareas:crear`, `tareas:ver`, `tareas:comentar` (granularidad innecesaria para este módulo).

## Risks / Trade-offs

- **[Riesgo] `contexto_id` sin FK** → puede quedar huérfano si la entidad referenciada se borra (soft-delete mitiga, pero no elimina el riesgo). Mitigación: documentar que es una referencia débil, no resolverla en esta etapa.
- **[Riesgo] Alto volumen sin paginación** → el listado admin sin límite puede ser pesado. Mitigación: aplicar paginación por defecto con `limit=50, offset=0` en `GET /api/tareas`.
- **[Trade-off] Máquina de estados simple** → no hay historial de transiciones de estado (solo estado actual). Para auditoría, `AuditLog` con `TAREA_ESTADO` registra los cambios pero no en la tabla `tarea` misma.

## Migration Plan

1. Migración `013_tareas_internas`: crea tablas `tarea` y `comentario_tarea`, índices, seed de permisos.
2. No hay downtime necesario (nuevas tablas, sin ALTER de existentes).
3. Rollback: ejecutar `downgrade` que dropea tablas y permisos seedeados.

## Open Questions

*(ninguna — el dominio está completamente definido en la KB)*
