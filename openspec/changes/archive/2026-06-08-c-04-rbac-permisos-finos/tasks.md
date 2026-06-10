## 1. Modelos SQLAlchemy

- [x] 1.1 Crear `app/models/rbac.py` con los modelos `Rol`, `Permiso` y `RolPermiso` usando `TenantScopedMixin`. Unicidades: `(tenant_id, nombre)` en `Rol` y `Permiso`; `(rol_id, permiso_id)` en `RolPermiso`.
- [x] 1.2 Exportar los nuevos modelos desde `app/models/__init__.py` para que Alembic los detecte.

## 2. Migración Alembic

- [x] 2.1 Crear `backend/alembic/versions/003_rbac.py` que crea las tablas `rol`, `permiso`, `rol_permiso` con todos sus constraints e índices.
- [x] 2.2 Agregar seed idempotente (`INSERT ... ON CONFLICT DO NOTHING`) en `upgrade()`: los 7 roles del dominio (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS) y la matriz de permisos de `03_actores_y_roles.md §3.3` para cada tenant existente.
- [x] 2.3 Implementar `downgrade()` con DROP TABLE en orden inverso respetando FKs.

## 3. Lógica de permisos

- [x] 3.1 Implementar `app/core/permissions.py`: función `get_user_permissions(roles: list[str], tenant_id: UUID, session: AsyncSession) -> set[str]` que resuelve la unión de permisos de los roles del usuario via DB query (JOIN `rol` → `rol_permiso` → `permiso`).
- [x] 3.2 Implementar `require_permission(permission: str)` en `app/core/permissions.py`: función que retorna un `Depends` de FastAPI. Interno: llama `get_current_user` + `get_db`, ejecuta `get_user_permissions`, verifica membresía; 403 si falta el permiso.

## 4. Repositorio RBAC

- [x] 4.1 Crear `app/repositories/rbac.py` con `RbacRepository(TenantScopedRepository[Rol])` y métodos:
  - `get_permissions_for_roles(role_names: list[str]) -> set[str]` — query para la resolución de permisos.
  - `get_rol_by_name(nombre: str) -> Rol | None`.

## 5. Tests — Safety net y TDD

- [x] 5.1 **Safety net**: ejecutar la suite existente y confirmar que todos los tests pasan antes de tocar código.
- [x] 5.2 Crear `backend/tests/test_rbac_models_tdd.py`:
  - Unicidad `(tenant_id, nombre)` en `Rol` es enforceada por DB.
  - Unicidad `(tenant_id, nombre)` en `Permiso` es enforceada por DB.
  - El mismo nombre de rol puede existir en tenants distintos (sin conflicto).
- [x] 5.3 Crear `backend/tests/test_rbac_seed_tdd.py`:
  - Después de la migración `003_rbac`, cada tenant tiene los 7 roles del dominio.
  - Seed es idempotente: segunda ejecución no duplica ni produce error.
- [x] 5.4 Crear `backend/tests/test_rbac_permissions_tdd.py`:
  - Usuario con un rol resuelve sus permisos correctamente.
  - Usuario con múltiples roles recibe la unión de permisos (sin duplicados).
  - Usuario sin roles tiene conjunto de permisos vacío.
  - Permisos de tenant A no se filtran en tenant B.
- [x] 5.5 Crear `backend/tests/test_rbac_guard_tdd.py`:
  - Usuario con permiso → 200 en endpoint protegido.
  - Usuario sin el permiso → 403.
  - Request sin Authorization header → 401.
  - Endpoint con permiso inexistente → 403 (fail-closed).

## 6. Integración y verificación final

- [x] 6.1 Ejecutar suite completa: `pytest backend/tests/ -v` — todos los tests deben pasar (incluyendo los de C-01/C-02/C-03).
- [x] 6.2 Verificar cobertura: `pytest --cov=app/core/permissions --cov=app/repositories/rbac --cov-report=term-missing` — ≥80% líneas, ≥90% reglas de negocio.
- [x] 6.3 Confirmar que `app/core/permissions.py` ya no es un stub: tiene implementación completa y exporta `require_permission`.
