## Why

`foundation-setup` dejó el esqueleto listo, pero el contrato crítico de activia-trace sigue vacío: no existe `Tenant`, no hay modelos base con lifecycle/auditoría, los repositories todavía no fail-close por tenant y no existe el baseline de migraciones para empezar a persistir dominio real. C-02 materializa ADR-002 y las reglas duras de aislamiento row-level antes de auth, RBAC y entidades académicas.

## What Changes

- Crear el modelo raíz `Tenant` y separar el lifecycle común (`id`, timestamps, soft delete) del scope multi-tenant (`tenant_id`) para evitar un `tenant_id` circular en la propia raíz.
- Definir mixins/convenciones ORM para UUID interno, `created_at`, `updated_at` y `deleted_at` en todas las entidades de negocio.
- Introducir un repository genérico que requiera contexto de tenant y aplique filtros por `tenant_id` + exclusión de soft delete por defecto.
- Agregar utilidad AES-256 reutilizable para campos cifrados en reposo, alineada con `ENCRYPTION_KEY` y sin exposición de plaintext en errores/logs.
- Crear la migración Alembic `001_tenant` y dejar fijada la convención de “una migración por cambio de schema”.
- Especificar pruebas obligatorias para aislamiento multi-tenant, soft delete, round-trip de cifrado y timestamps automáticos.

## Capabilities

### New Capabilities
- `tenant-core-models`: modelo `Tenant` y convenciones ORM de UUID, timestamps y soft delete para entidades raíz y tenant-scoped.
- `tenant-scoped-repositories`: repository base fail-closed con scope de tenant siempre activo y borrado lógico por defecto.
- `encrypted-fields-at-rest`: utilidad AES-256 para cifrar/descifrar atributos sensibles sin exponer plaintext.
- `schema-migration-baseline`: baseline Alembic `001_tenant` y convención secuencial de migraciones de schema.

### Modified Capabilities
- Ninguna.

## Impact

- Backend: `backend/app/models/`, `backend/app/repositories/`, `backend/app/core/tenancy.py`, `backend/app/core/security.py`, `backend/alembic/`, `backend/tests/`.
- Persistencia: metadata ORM y primera migración de dominio.
- Gobernanza: change **CRÍTICO**; bloquea C-03/C-04 y explicita aislamiento de tenant como invariante testeable.
