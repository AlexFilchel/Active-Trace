## Why

Tras cerrar C-01…C-24 se pidió una revisión general del proyecto: correr toda la test suite (backend + frontend) y arreglar lo que apareciera. La corrida reveló dos problemas reales que no eran visibles change por change: una migración con `downgrade()` incompleto en el módulo de liquidaciones, y un patrón de leak de estado entre archivos de test que rompía 22 tests del backend solo cuando corrían en la suite completa (pasaban en aislamiento, lo que ocultó el problema durante el desarrollo de C-01…C-24).

Ninguno de estos dos problemas constituye una feature nueva: son correcciones de robustez sobre trabajo ya entregado. Se documentan como change para mantener la misma trazabilidad que el resto del roadmap.

## What Changes

- **Fix de migración** (`016_liquidaciones_honorarios`, dominio CRÍTICO de liquidaciones): `downgrade()` estaba vacío (`pass`), lo que rompía cualquier downgrade de migraciones anteriores en la cadena (`DependentObjectsStillExistError` al intentar tirar `usuario`/`cohorte` con FKs vivas desde `liquidacion`/`factura`). Se implementó el downgrade completo y simétrico al upgrade: borra permisos/rol_permiso seedeados, `factura`, `liquidacion` (+ índice), `salario_plus` (+ índice), `salario_base` (+ índice), columna `materia.categoria_plus`.
- **Fix de aislamiento de tests** (backend, 7 archivos): varios fixtures de test dejaban filas de `Tenant`/`AuthUser`/`AuditLog`/`Carrera` sin limpiar al terminar el último test del archivo (usaban `return {...}` en vez de `yield`+teardown, o hacían `delete()` puntual en vez de `TRUNCATE CASCADE`). Esto rompía en cascada a los pocos archivos que limpian con `delete()` selectivo en su setup, con un síntoma que cambiaba de archivo en archivo según qué tabla quedaba huérfana (`audit_log→auth_user`, luego `auth_user→tenant`, luego `carrera→tenant`).
- **Sincronización de entorno**: se detectó que `docker cp` sin trailing `/.` deja el contenedor del backend con archivos de test desactualizados respecto al host cuando el directorio destino ya existe — causa de una falsa señal de 16 tests rotos que en realidad ya estaban arreglados en el host.

## Capabilities

### Modified Capabilities

- `liquidaciones-y-honorarios`: la migración `016_liquidaciones_honorarios` ahora es reversible (downgrade completo). No cambia comportamiento de runtime, solo la capacidad operativa de revertir el schema.

No se agregan ni modifican capacidades de producto — este change es puramente de robustez de migraciones y de la test suite.

## Impact

- **Migración Alembic**: `016_liquidaciones_honorarios.py` — `downgrade()` implementado.
- **Tests backend modificados** (sin cambios de comportamiento de producción):
  - `tests/test_audit_appendonly_tdd.py` — cleanup en `finally` tras los tests del trigger de append-only.
  - `tests/test_auditoria_acciones_scope_tdd.py`, `tests/test_auditoria_log_tdd.py`, `tests/test_auditoria_comunicaciones_interacciones_tdd.py` — fixture `ctx` convertido de `return` a `yield` + limpieza en teardown.
  - `tests/test_core_models_tdd.py`, `tests/test_tenant_repository_tdd.py`, `tests/test_impersonation_tdd.py` — `delete()` puntual reemplazado por `clean_database()` (TRUNCATE CASCADE vía `tests/usuarios_test_utils.py`).
- **Resultado verificado**: backend 430/430 tests passed (0 failed, 0 errors; partía de 16 failed + 22 errors). Frontend 33 archivos / 278 tests passed, `npm run lint` sin hallazgos.
- **Governance**: el fix de la migración de liquidaciones (dominio CRÍTICO) se implementó solo tras aprobación explícita del usuario. Los fixes de test son de governance BAJO (no tocan lógica de negocio ni dominios sensibles).
- Sin cambios de API, sin cambios de esquema más allá de la migración existente, sin nuevas dependencias.
