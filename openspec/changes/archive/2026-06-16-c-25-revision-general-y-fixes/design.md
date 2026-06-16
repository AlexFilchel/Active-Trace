## Context

Pedido del usuario: "haz una revisión general, pruebas, test lo que haga falta" tras archivar C-01…C-24. No hay feature nueva detrás de este change — es una auditoría de salud del proyecto vía test suite completa (backend + frontend) y la corrección de lo que esa corrida encontró.

Governance: el primer hallazgo cae en dominio CRÍTICO (migración de liquidaciones) y requirió aprobación explícita antes de escribir código, según [03_actores_y_roles.md] / reglas del repo. El resto son fixtures de test (governance BAJO): no tocan lógica de negocio, solo higiene de aislamiento entre tests.

## Goals / Non-Goals

**Goals:**
- Backend test suite 100% verde corriendo completa (no solo archivo por archivo).
- Frontend test suite 100% verde + lint limpio.
- Migración `016_liquidaciones_honorarios` reversible de punta a punta.
- Documentar la causa raíz de cada falla para que no se repita el mismo patrón en changes futuros.

**Non-Goals:**
- No se tocó lógica de negocio ni endpoints de producción.
- No se agregó cobertura nueva — se corrigió aislamiento de la que ya existía.
- No se resolvieron los pendientes ya conocidos de sesiones previas (AdminPage faltante, queries directas en routers, `get_by_raw_token()` sin filtro de tenant) — quedan fuera de este change por decisión explícita de alcance.

## Decisions

### D1 — `downgrade()` completo y simétrico al `upgrade()` en 016

La migración creaba 4 tablas + 1 columna + seed de permisos en `upgrade()`, pero `downgrade()` era `pass`. Cualquier intento de bajar una migración anterior en la cadena (que las migraciones de test sí hacen, para probar idempotencia) fallaba con `DependentObjectsStillExistError` porque `liquidacion`/`factura` mantenían FKs vivas hacia `usuario`/`cohorte`.

Decisión: implementar el reverso mecánico exacto — borrar en orden inverso de dependencia (rol_permiso/permiso seedeados → `factura` → `liquidacion` + índice → `salario_plus` + índice → `salario_base` + índice → columna `materia.categoria_plus`). No se generalizó ni se introdujo abstracción: es el espejo línea por línea del `upgrade()`.

### D2 — Causa raíz del leak de test state: fixtures que limpian solo al setup

Patrón dominante en el repo: los fixtures llaman `clean_database()` (TRUNCATE CASCADE sobre todas las tablas de `Base.metadata`) al **inicio** de cada test, confiando en que el test que corra después también limpiará al empezar. Esto funciona mientras todos los consumidores usen `clean_database()`.

El problema apareció en los pocos fixtures que en cambio hacían `delete()` selectivo sobre una lista fija de tablas (`test_core_models_tdd.py`, `test_tenant_repository_tdd.py`, `test_impersonation_tdd.py`): su lista no incluía todas las tablas que un archivo anterior pudo haber dejado con filas (`audit_log`, `carrera`, etc.), así que el `DELETE FROM tenant`/`auth_user` fallaba por FK.

Decisión: en vez de perseguir cada fixture que "no limpia al final" (patrón extendido y tolerado en el resto del repo), se hizo robusto el lado que sí importa — los pocos consumidores con `delete()` selectivo pasaron a usar `clean_database()`, igual que el resto de la suite. Tres fixtures que sí limpiaban con `return` en vez de `yield` (`test_auditoria_acciones_scope_tdd.py`, `test_auditoria_log_tdd.py`, `test_auditoria_comunicaciones_interacciones_tdd.py`) se corrigieron también, agregando teardown explícito, porque eran la fuente más directa y fácil de cerrar del primer síntoma observado (leak de `audit_log`/`auth_user`).

### D3 — No se introdujo un fixture global de limpieza de sesión

Se consideró agregar un `autouse` fixture de sesión que hiciera `clean_database()` antes de cada test sin excepción, eliminando el problema de raíz para toda la suite. Se descartó para este change: cambiaría el comportamiento de fixtures que dependen de estado sembrado por *otro* fixture en el mismo archivo (varios tests comparten tenant/usuarios dentro de un mismo archivo a propósito), y es un cambio de mayor alcance que el que pidió el usuario. Queda anotado como mejora futura si se repite este tipo de falla.

### D4 — `docker cp` con trailing `/.`

No es una decisión de diseño del producto, sino un hallazgo operativo: `docker cp src container:/dest` sin el `/.` final anida el directorio en vez de sobreescribir su contenido cuando `/dest` ya existe. Esto generó una falsa señal (16 tests "rotos" que en realidad ya estaban arreglados en el host, corriendo stale en el container). Se documenta para que futuras sesiones no repitan el diagnóstico desde cero.
