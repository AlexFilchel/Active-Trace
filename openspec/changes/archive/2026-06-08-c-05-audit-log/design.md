## Context

El sistema tiene un modelo de seguridad multi-tenant con RBAC (C-04), autenticación JWT (C-03) y soft delete transversal. Sin embargo, ninguna acción significativa queda registrada: no hay trazabilidad de quién importó calificaciones, quién cerró una liquidación ni quién inició una impersonación. `trace` es el nombre del producto — el audit log es la razón de ser del sistema.

**Constraint clave**: el log de auditoría es append-only. Un registro creado nunca puede modificarse ni eliminarse, ni a nivel aplicación ni a nivel base de datos. Esta garantía debe ser estructural, no solo convencional.

---

## Goals / Non-Goals

**Goals:**
- `AuditLog` model inmutable con enforcement a dos niveles (app + DB).
- Helper `audit_action(...)` de uso sencillo desde cualquier service/router.
- Impersonación controlada: emitir token distinguible, atribuir acciones al actor real, registrar inicio/fin.
- Migración `004_audit_log` con trigger de append-only en PostgreSQL.

**Non-Goals:**
- Panel de consulta de auditoría (C-19 lo construye sobre este modelo).
- Paginación/filtros de audit log (C-19).
- Auditoría automática de todos los modelos (magic ORM hooks) — se audita explícitamente desde el código de negocio.
- Rate limiting de impersonación (ADMIN scope es suficiente por ahora).

---

## Decisions

### D1 — Enforcement append-only a dos niveles

**Decisión**:
1. **App level**: `AuditLog` no hereda `TenantScopedMixin` completo. Usa un `AuditMixin` propio con `id`, `tenant_id`, `fecha_hora` — sin `updated_at`, sin `deleted_at`. El repositorio `AuditLogRepository` solo expone `create` y `list`/`get`; no tiene `update`, `soft_delete` ni `delete`.
2. **DB level**: la migración agrega un trigger PostgreSQL `audit_log_immutable` que ejecuta `RAISE EXCEPTION` en `UPDATE` y `DELETE` sobre `audit_log`. Hace fallar cualquier intento aunque alguien acceda directamente a la DB.

**Alternativa descartada**: solo enforcement a nivel app (sin trigger). Descartada porque un acceso directo a la DB (migración errónea, herramienta externa, bug) podría borrar registros sin que la app lo sepa.

**Alternativa descartada**: usar PostgreSQL row-level security con `GRANT INSERT, SELECT` al usuario de la app (revocar UPDATE/DELETE). Descartada porque requiere gestión de múltiples roles de DB, complejiza el setup de desarrollo y no es compatible con el docker-compose single-user típico del proyecto.

---

### D2 — `AuditMixin` separado de `TenantScopedMixin`

**Decisión**: `AuditLog` usa un `AuditMixin` en `app/models/audit.py` con columnas `id`, `tenant_id`, `fecha_hora`. No hereda `TenantScopedMixin` porque ese mixin incluye `updated_at` y `deleted_at` — semánticamente incorrectos para un registro inmutable.

**Consecuencia**: `AuditLogRepository` no extiende `TenantScopedRepository` genérico (que expone `update` y `soft_delete`). Tiene su propia implementación mínima.

---

### D3 — `audit_action` como función async simple, no decorador

**Decisión**: el helper es una función `async def audit_action(*, session, actor_id, tenant_id, accion, detalle=None, materia_id=None, filas_afectadas=0, ip=None, user_agent=None, impersonando_id=None)` que crea un `AuditLog` y hace `session.flush()`.

**Alternativa descartada**: decorador `@audit("CODIGO_ACCION")` sobre funciones de service. Descartado porque:
- Acopla la auditoría a la firma del decorator (requiere que la función reciba `session`, `current_user`, etc. en posiciones fijas).
- Oculta el flujo de control: no es obvio desde el código que una función audita.
- Los detalles variables (filas_afectadas, materia_id) son difíciles de capturar automáticamente.

**Por qué función simple**: explícita, testeable, composable. El llamador decide qué auditar y con qué contexto.

---

### D4 — Impersonación mediante claim adicional en el JWT

**Decisión**: la impersonación emite un nuevo access token con un claim adicional `impersonating_user_id: str`. Cuando este claim está presente:
- `current_user.user_id` = usuario que impersona (actor real).
- `current_user.impersonating_user_id` = usuario impersonado.
- El `audit_action` helper siempre toma `actor_id = current_user.user_id` (actor real).

**Flujo**:
```
POST /api/auth/impersonate/{target_user_id}   ← requiere impersonacion:usar
  → verifica permiso, emite access token con impersonating_user_id
  → registra IMPERSONACION_INICIAR en AuditLog

POST /api/auth/impersonate/end
  → revoca sesión de impersonación
  → registra IMPERSONACION_FINALIZAR en AuditLog
```

**Alternativa descartada**: sesión separada en DB para impersonación (estado server-side). Descartada porque agrega complejidad de gestión de estado. El JWT es stateless y la TTL corta (15min) limita el riesgo.

**Trade-off aceptado**: si el actor real rota su refresh token mientras hay una sesión de impersonación activa, el access token de impersonación sigue válido hasta su TTL. Aceptable dado el TTL de 15 minutos.

---

### D5 — `AuthenticatedUser` agrega campo opcional `impersonating_user_id`

**Decisión**: `AuthenticatedUser` dataclass agrega `impersonating_user_id: uuid.UUID | None = None`. El factory en `get_current_user` lo extrae del claim JWT si está presente.

**Por qué**: permite que cualquier endpoint o helper detecte si la sesión actual es de impersonación sin acceder a la DB.

---

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| El trigger de DB ralentiza inserciones masivas en audit_log | Aceptado: el trigger solo actúa en UPDATE/DELETE, que no deberían ocurrir. Los INSERT no sufren overhead. |
| Un bug en `audit_action` puede romper el flujo principal si lanza excepción | `audit_action` es llamado dentro de la misma transacción que la acción auditada. Si falla, falla toda la transacción — esto es deseable (si no se puede auditar, no se ejecuta la acción). |
| El claim `impersonating_user_id` en el JWT puede confundir a middleware que no lo conoce | El claim es aditivo y opcional; `get_current_user` lo ignora si no está presente. No rompe código existente. |
| El trigger de append-only puede interferir con migraciones futuras que necesiten corregir datos | Si se necesita corrección de datos en producción (raro), debe hacerse con una migración explícita que desactive el trigger temporalmente — proceso deliberado y auditado. |

---

## Migration Plan

1. `004_audit_log.py`: crea tabla `audit_log` con todos los campos de E-AUD.
2. Mismo archivo: agrega trigger `audit_log_immutable` que rechaza UPDATE/DELETE.
3. `downgrade()`: DROP TRIGGER + DROP TABLE.
4. Sin seed de datos (el log empieza vacío).
5. Sin cambios breaking en tablas existentes.

---

## Open Questions

_(ninguna — E-AUD está completamente definido en `knowledge-base/04_modelo_de_datos.md` y el modelo de impersonación en `03_actores_y_roles.md §4`)_
