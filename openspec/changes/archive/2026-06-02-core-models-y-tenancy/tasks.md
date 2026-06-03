## 1. Modelos core y convenciones ORM

- [x] 1.1 (RED) Escribir tests que definan el contrato de `Tenant`, `UuidLifecycleMixin` y `TenantScopedMixin`: UUID interno, timestamps automáticos y `deleted_at` nulo por defecto.
- [x] 1.2 (GREEN) Implementar los modelos/mixins base en `backend/app/models/` y enlazarlos a `Base.metadata` sin introducir entidades fuera de scope.
- [x] 1.3 (TRIANGULATE) Agregar casos para actualización de `updated_at` y para soft delete marcando `deleted_at` sin borrado físico.

## 2. Repository base con aislamiento multi-tenant

- [x] 2.1 (RED) Escribir tests de repository que fallen si falta `tenant_id`, que impidan leer datos de otro tenant y que excluyan soft-deleted por defecto.
- [x] 2.2 (GREEN) Implementar el repository genérico tenant-scoped en `backend/app/repositories/` con API fail-closed y borrado lógico.
- [x] 2.3 (TRIANGULATE) Cubrir casos de `include_deleted` explícito y de actualización restringida al tenant actual.

## 3. Cifrado AES-256 reutilizable

- [x] 3.1 (RED) Escribir tests para round-trip de cifrado/descifrado, ciphertext distinto al plaintext y fallo seguro con clave incorrecta o payload inválido.
- [x] 3.2 (GREEN) Implementar la utilidad AES-256 en `backend/app/core/security.py` usando `ENCRYPTION_KEY` y una interfaz reutilizable por futuros modelos.
- [x] 3.3 (TRIANGULATE) Agregar casos de strings vacíos/Unicode y verificar que errores o logs no incluyan plaintext sensible.

## 4. Baseline Alembic de dominio

- [x] 4.1 (RED) Escribir una prueba/verificación que falle si `001_tenant` no crea la tabla `tenant` con su lifecycle esperado o si la metadata no queda alineada.
- [x] 4.2 (GREEN) Crear la migración Alembic `001_tenant` y ajustar la configuración necesaria para autogenerate consistente con los modelos core.
- [x] 4.3 (TRIANGULATE) Verificar upgrade/downgrade del baseline y documentar la convención secuencial de “una migración por cambio de schema”.

## 5. Verificación crítica del change

- [x] 5.1 Ejecutar la suite relevante con PostgreSQL real (sin mocks de DB) y confirmar verde los casos de aislamiento multi-tenant, soft delete, cifrado y timestamps.
- [x] 5.2 Confirmar que el diseño mantiene desacoplado tenant scope de HTTP/JWT y deja listos `core/tenancy.py`, `core/security.py` y `repositories/` para C-03/C-04.
- [x] 5.3 Revisar que ningún path crítico viole las reglas duras de `AGENTS.md` (soft delete siempre, UUID interno, tenant scope obligatorio, una migración por cambio de schema).
