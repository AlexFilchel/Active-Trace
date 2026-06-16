## 1. Diagnóstico

- [x] 1.1 Correr backend test suite completa y relevar fallas reales (no por archivo aislado).
- [x] 1.2 Detectar y corregir desincronización host/contenedor (`docker cp` sin trailing `/.`) que enmascaraba fixes ya aplicados en host.
- [x] 1.3 Identificar causa raíz de `DependentObjectsStillExistError` en tests de migración → `downgrade()` vacío en `016_liquidaciones_honorarios.py`.

## 2. Fix de migración (dominio CRÍTICO — requiere aprobación explícita)

- [x] 2.1 Presentar hallazgo y plan de fix al usuario antes de escribir código (governance CRÍTICO).
- [x] 2.2 Implementar `downgrade()` completo en `016_liquidaciones_honorarios.py` (reverso simétrico del `upgrade()`).
- [x] 2.3 Verificar: suite de migraciones pasa de 5 failed → 0 failed.

## 3. Fix de aislamiento de tests (governance BAJO)

- [x] 3.1 Diagnosticar el leak de estado entre archivos (`audit_log`→`auth_user`→`tenant`→`carrera`) re-corriendo la suite completa tras cada fix parcial.
- [x] 3.2 Cleanup en `finally` en `test_audit_appendonly_tdd.py` (tests del trigger append-only).
- [x] 3.3 Convertir `ctx` de `return` a `yield` + teardown en `test_auditoria_acciones_scope_tdd.py`, `test_auditoria_log_tdd.py`, `test_auditoria_comunicaciones_interacciones_tdd.py`.
- [x] 3.4 Reemplazar `delete()` selectivo por `clean_database()` en `test_core_models_tdd.py`, `test_tenant_repository_tdd.py`, `test_impersonation_tdd.py`.
- [x] 3.5 Verificar: backend test suite completa → 430 passed, 0 failed, 0 errors.

## 4. Verificación frontend

- [x] 4.1 Correr `npm test` (vitest) completo.
- [x] 4.2 Correr `npm run lint`.
- [x] 4.3 Verificar: 33 archivos / 278 tests passed, lint sin hallazgos.

## 5. Cierre

- [x] 5.1 Documentar este change (proposal/design/tasks) reflejando trabajo ya completado y verificado.
