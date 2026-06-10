## 1. Modelo y mixin de auditoría

- [x] 1.1 Crear `app/models/audit.py` con `AuditMixin` (id UUID, tenant_id, fecha_hora — sin updated_at ni deleted_at) y modelo `AuditLog` con todos los campos de E-AUD (`actor_id`, `impersonado_id`, `materia_id`, `accion`, `detalle` JSONB, `filas_afectadas`, `ip`, `user_agent`).
- [x] 1.2 Exportar `AuditLog` desde `app/models/__init__.py`.

## 2. Repositorio append-only

- [x] 2.1 Crear `app/repositories/audit.py` con `AuditLogRepository`: solo expone `create(...)` y métodos de lectura (`get`, `list`). Sin `update`, sin `soft_delete`, sin `delete`.
- [x] 2.2 Exportar `AuditLogRepository` desde `app/repositories/__init__.py`.

## 3. Helper de auditoría

- [x] 3.1 Crear `app/core/audit.py` con la función `async def audit_action(*, session, actor_id, tenant_id, accion, detalle=None, materia_id=None, filas_afectadas=0, ip=None, user_agent=None, impersonando_id=None)` que crea un `AuditLog` y hace `session.flush()`.

## 4. Migración Alembic

- [x] 4.1 Crear `backend/alembic/versions/004_audit_log.py` que crea la tabla `audit_log` con todos sus campos, índices (`tenant_id`, `actor_id`, `fecha_hora`) y constraints.
- [x] 4.2 En la misma migración, agregar el trigger PostgreSQL `audit_log_immutable` (`BEFORE UPDATE OR DELETE ON audit_log`) que lanza `RAISE EXCEPTION 'audit_log is append-only'`.
- [x] 4.3 Implementar `downgrade()`: DROP TRIGGER + DROP TABLE en orden correcto.

## 5. Impersonación

- [x] 5.1 Extender `AuthenticatedUser` en `app/core/dependencies.py` con `impersonating_user_id: uuid.UUID | None = None`. Actualizar `get_current_user` para extraer el claim del JWT si está presente.
- [x] 5.2 Crear función `create_impersonation_token(*, actor_user_id, impersonated_user_id, tenant_id, roles)` en `app/core/security.py` que emite un JWT con el claim adicional `impersonating_user_id`.
- [x] 5.3 Agregar lógica de impersonación en `app/services/auth.py`: `impersonate_user(actor, target_user_id, session)` — verifica que el target pertenece al mismo tenant, emite token, registra `IMPERSONACION_INICIAR` vía `audit_action`.
- [x] 5.4 Agregar `POST /api/auth/impersonate/{user_id}` en `app/api/v1/routers/auth.py` con guard `require_permission("impersonacion:usar")`. Responde con el nuevo access token.
- [x] 5.5 Agregar `POST /api/auth/impersonate/end` que registra `IMPERSONACION_FINALIZAR` y retorna 204.

## 6. Tests — Safety net y TDD

- [x] 6.1 **Safety net**: ejecutar la suite existente y confirmar que todos los tests pasan antes de tocar código.
- [x] 6.2 Crear `backend/tests/test_audit_model_tdd.py`:
  - `AuditLog` puede crearse con todos sus campos.
  - `AuditLog` no tiene `deleted_at` ni `updated_at`.
  - `AuditLogRepository` no expone métodos de modificación.
- [x] 6.3 Crear `backend/tests/test_audit_appendonly_tdd.py`:
  - UPDATE directo en la tabla `audit_log` desde la DB es rechazado por el trigger.
  - DELETE directo en la tabla `audit_log` desde la DB es rechazado por el trigger.
- [x] 6.4 Crear `backend/tests/test_audit_helper_tdd.py`:
  - `audit_action` crea registro con código y filas_afectadas.
  - `audit_action` con detalle JSON persiste el JSON correctamente.
  - `audit_action` sin `materia_id` persiste `NULL`.
  - Aislamiento: registros de tenant A no visibles desde tenant B.
- [x] 6.5 Crear `backend/tests/test_impersonation_tdd.py`:
  - Sin permiso `impersonacion:usar` → 403.
  - Con permiso → token con claim `impersonating_user_id`.
  - Token de impersonación tiene `user_id = actor_real`.
  - `IMPERSONACION_INICIAR` registrado al iniciar.
  - `IMPERSONACION_FINALIZAR` registrado al finalizar (endpoint `/impersonate/end`).
  - Acción realizada bajo impersonación tiene `actor_id = actor_real`, `impersonado_id = target`.

## 7. Integración y verificación final

- [x] 7.1 Ejecutar suite completa: `pytest backend/tests/ -v` — todos los tests deben pasar (incluyendo C-01/C-02/C-03/C-04).
- [x] 7.2 Verificar cobertura: `pytest --cov=app/core/audit --cov=app/repositories/audit --cov=app/models/audit --cov-report=term-missing` — ≥80% líneas, ≥90% reglas de negocio.
- [x] 7.3 Confirmar que el trigger append-only aparece en el schema de la DB de test ejecutando la migración `004_audit_log`.
