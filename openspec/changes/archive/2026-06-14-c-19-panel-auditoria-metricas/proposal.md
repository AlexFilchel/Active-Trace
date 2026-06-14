## Why

El sistema genera un log de auditoría completo desde C-05, pero no expone ninguna API de consulta. COORDINADOR y ADMIN no tienen forma de supervisar la actividad del sistema ni revisar el historial de acciones. Este change cierra esa brecha: endpoints de solo lectura sobre `AuditLog` con agregaciones y filtros, sin tocar ningún modelo existente.

## What Changes

- Nuevo permiso `auditoria:ver` para ADMIN, COORDINADOR y FINANZAS.
- `GET /api/auditoria/acciones-por-dia` — serie temporal de volumen de acciones.
- `GET /api/auditoria/estado-comunicaciones` — resumen de estado de comunicaciones agrupado por docente.
- `GET /api/auditoria/interacciones-docente` — métricas de acciones por docente × materia.
- `GET /api/auditoria/log` — log paginado de últimas acciones (limit configurable, default 200).
- Scope `(propio)` para COORDINADOR: solo ve acciones propias. ADMIN y FINANZAS ven todo el tenant.
- Sin nuevos modelos ni migraciones de schema (solo seed de permiso).

## Capabilities

### New Capabilities
- `panel-auditoria`: endpoints de consulta y agregación sobre AuditLog — acciones por día, estado de comunicaciones, interacciones por docente×materia y log paginado con filtros.

### Modified Capabilities
_(ninguna — solo lectura sobre AuditLog existente)_

## Impact

- **Nuevo**: `app/repositories/auditoria.py`, `app/services/auditoria_service.py`, `app/api/v1/routers/auditoria.py`, `app/schemas/auditoria.py`.
- **Migración**: `015_auditoria_permiso.py` — solo seed del permiso `auditoria:ver` (sin ALTER de tablas).
- **Dependencias**: `C-05` (AuditLog model), `C-07` (usuarios para scope propio).
