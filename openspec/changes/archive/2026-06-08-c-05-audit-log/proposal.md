## Why

El sistema procesa acciones críticas (importaciones, comunicaciones, liquidaciones, cambios de estructura) sin ningún registro trazable: no hay forma de responder "quién hizo qué, cuándo y con qué resultado". C-05 construye el log de auditoría append-only que convierte `trace` en su nombre — toda acción significativa queda registrada y atribuida, con soporte para impersonación controlada.

## What Changes

- Nuevo modelo `AuditLog` (E-AUD): registro inmutable de acciones significativas con actor, impersonado, materia, código de acción, detalle JSON, filas afectadas, IP y user-agent.
- Enforcement **append-only** a nivel app (sin método update/delete) y a nivel DB (constraint o trigger).
- Helper de auditoría `audit_action(...)` para registrar acciones desde services/routers con código estandarizado (`CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, etc.).
- **Impersonación**: endpoint `POST /api/auth/impersonate/{user_id}` que emite una sesión distinguible para usuarios con `impersonacion:usar`. Toda acción bajo impersonación queda atribuida al actor real (no al impersonado). Registra `IMPERSONACION_INICIAR` y `IMPERSONACION_FINALIZAR`.
- Migración `004_audit_log`: crea la tabla `audit_log` con constraints de append-only.

## Capabilities

### New Capabilities
- `audit-log`: Registro append-only de acciones significativas (E-AUD), helper de auditoría con códigos estandarizados, e impersonación controlada con atribución al actor real.

### Modified Capabilities

_(ninguna — C-05 no modifica requisitos de capacidades ya especificadas)_

## Impact

- **Nueva tabla**: `audit_log` — sin soft delete, sin update, sin delete físico.
- **Migración**: `004_audit_log.py`.
- **`app/models/audit.py`**: modelo `AuditLog`.
- **`app/core/audit.py`**: helper `audit_action(session, actor_id, tenant_id, accion, ...)`.
- **`app/api/v1/routers/auth.py`**: nuevos endpoints `POST /api/auth/impersonate/{user_id}` y `POST /api/auth/impersonate/end`.
- **`app/core/dependencies.py`**: `AuthenticatedUser` se extiende con `impersonating_user_id: UUID | None` para sesiones de impersonación.
- **`app/services/auth.py`**: lógica de impersonación (emitir token distinguible, verificar permiso `impersonacion:usar`).
- Todos los routers que registren acciones de auditoría dependen del helper de este change (C-08, C-09, C-11, C-12, etc.).
