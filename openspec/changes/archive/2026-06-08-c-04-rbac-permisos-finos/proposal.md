## Why

Con C-03 el sistema puede autenticar usuarios, pero todos los endpoints más allá de `/health` y `/auth` quedan desprotegidos: no hay forma de declarar qué permiso exige cada acción ni de verificarlo. C-04 construye la capa de autorización que permite a todos los changes siguientes (C-05 en adelante) proteger sus endpoints con `require_permission("modulo:accion")`.

## What Changes

- Nuevas tablas `Rol`, `Permiso` y `RolPermiso` como catálogo administrable por tenant (no hardcodeado en código).
- Seed inicial con los 7 roles del dominio (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS) y la matriz de permisos base definida en `03_actores_y_roles.md §3.3`.
- Dependency/guard `require_permission("modulo:accion")` que declara el permiso requerido por endpoint; sin permiso explícito → 403 (fail-closed).
- Resolución de permisos efectivos server-side por request: unión de todos los roles del usuario, acotada por tenant y vigencia de la asignación (vigencia que será completada en C-07; por ahora se resuelve desde los roles del JWT).
- Migración Alembic `003_rbac`: crea `rol`, `permiso`, `rol_permiso` con seed incluido.
- `AuthenticatedUser` extiende su contrato para exponer `has_permission(modulo:accion)` sin cambiar el claim del JWT (los permisos se resuelven desde los roles del token, no se almacenan en él).

## Capabilities

### New Capabilities
- `rbac`: Sistema de autorización RBAC con permisos finos (`modulo:accion`). Cubre tablas de catálogo (Rol, Permiso, RolPermiso), seed de la matriz base, guard `require_permission`, y resolución server-side de permisos efectivos por request.

### Modified Capabilities

_(ninguna — C-04 introduce la capa de autorización sin modificar requisitos de capacidades ya especificadas)_

## Impact

- **Nuevas tablas**: `rol`, `permiso`, `rol_permiso` (todas con `tenant_id` y soft delete).
- **Migración**: `003_rbac.py`.
- **`app/core/permissions.py`**: implementación completa (hoy es un stub de una línea).
- **`app/core/dependencies.py`**: nuevo `require_permission()`, `AuthenticatedUser` con método de verificación.
- **Todos los routers futuros** (C-05 en adelante) dependen de este guard para declarar permisos.
- **Sin cambios breaking en el JWT**: el claim `roles` sigue siendo `list[str]` con los nombres de rol; los permisos se resuelven server-side en cada petición.
- **Dependencia directa**: C-05, C-06 y C-21 (primer fork) no pueden arrancar sin este change.
