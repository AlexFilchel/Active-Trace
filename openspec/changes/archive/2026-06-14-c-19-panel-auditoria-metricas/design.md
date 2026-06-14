## Context

El modelo `AuditLog` existe desde C-05 y acumula entradas para cada acción significativa del sistema. Hasta ahora no hay ningún endpoint que lo consulte. C-19 agrega una capa de solo lectura: un repositorio con agregaciones SQL, un servicio con lógica de scope, y cuatro endpoints bajo `/api/auditoria/`.

Governance: ALTO. El log de auditoría es la fuente de verdad de toda la actividad del tenant — no se modifica, solo se lee. Sin embargo, exponer datos de otros usuarios requiere control de scope estricto.

## Goals / Non-Goals

**Goals:**
- Endpoints de solo lectura sobre `AuditLog` con filtros y agregaciones.
- Scope `(propio)` para COORDINADOR: solo ve sus propias acciones.
- ADMIN y FINANZAS ven todo el tenant.
- Seed del permiso `auditoria:ver` en migración `015`.

**Non-Goals:**
- Modificación o eliminación de entradas de auditoría (append-only por diseño).
- Exportación a CSV o PDF (fuera del alcance MVP).
- Alertas en tiempo real sobre eventos de auditoría.
- Nuevas tablas o cambios de schema en `audit_log`.

## Decisions

### D1 — Sin nuevos modelos: solo lectura sobre AuditLog existente
**Decisión**: C-19 no introduce ninguna tabla nueva. Todas las queries trabajan directamente sobre `audit_log` (model `AuditLog` de C-05).

**Rationale**: el log ya tiene todos los campos necesarios (`accion`, `actor_id`, `tenant_id`, `created_at`, `detalle`, `ip`). Agregar tablas derivadas crearía duplicación de datos.

### D2 — Scope (propio) implementado en Service, no en Repository
**Decisión**: la restricción "COORDINADOR solo ve sus propias acciones" se aplica en `AuditoriaService` comparando `user.user_id` con `AuditLog.actor_id`. El repository siempre filtra por `tenant_id`.

**Rationale**: separación limpia — el repository garantiza aislamiento de tenant; el service aplica RBAC fino de scope.

**Alternativa descartada**: columna `scope` en el permiso (complejidad de RBAC innecesaria para MVP).

### D3 — Agregaciones en SQL (GROUP BY), no en Python
**Decisión**: `acciones_por_dia` y `interacciones_docente` se calculan con `GROUP BY` en la query, no con lista completa + groupby en Python.

**Rationale**: `audit_log` puede tener millones de filas; traer todo a Python es inviable. SQLAlchemy con `func.count()` y `func.date()` lo resuelve eficientemente.

### D4 — Estado de comunicaciones desde AuditLog, no desde Comunicacion
**Decisión**: el resumen de estado de comunicaciones se calcula contando acciones con prefijo `COMUNICACION_` agrupadas por `actor_id` y estado inferido del `accion`.

**Alternativa viable**: hacer un JOIN con la tabla `comunicacion`. Descartada para mantener C-19 independiente del modelo de comunicaciones.

### D5 — Límite de log configurable vía query param, default 200 (RN-F9.1)
**Decisión**: `GET /api/auditoria/log?limit=N` acepta hasta 500. Default 200 según la KB.

### D6 — Migración 015: solo seed de permiso
**Decisión**: la migración `015_auditoria_permiso.py` solo inserta el permiso `auditoria:ver` para los roles ADMIN, COORDINADOR y FINANZAS. Sin DDL (no hay tablas nuevas).

## Risks / Trade-offs

- **Performance en audit_log grande**: las agregaciones GROUP BY pueden ser lentas sin índice en `created_at` + `tenant_id`. Mitigación: el índice compuesto ya existe en C-05 (`ix_audit_log_tenant_id`); agregar `created_at` si el query plan lo requiere.
- **Estado de comunicaciones inferido**: interpretar el estado desde el código de acción (`COMUNICACION_ENVIO_OK`, etc.) es frágil si los códigos cambian. Mitigación: documentar los códigos como catálogo cerrado (RN-24).

## Migration Plan

1. Migración `015_auditoria_permiso.py`: seed de `auditoria:ver` para ADMIN, COORDINADOR, FINANZAS. Sin downtime.
2. Deploy de los nuevos endpoints. Sin cambios en tablas existentes → rollback limpio (solo eliminar los endpoints).
