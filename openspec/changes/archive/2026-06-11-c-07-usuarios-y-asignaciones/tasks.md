## 1. Models and migration

- [x] 1.1 Write RED tests for `Usuario`: tenant scope, soft delete, encrypted PII fields, default estado `Activo`, `(tenant_id, email_hash)` uniqueness.
- [x] 1.2 Implement `Usuario` model in `backend/app/models/usuarios.py` with `TenantScopedMixin`, nullable unique `auth_user_id`, encrypted columns and lookup hashes.
- [x] 1.3 Triangulate email normalization: same email case/spacing conflicts inside tenant; same email in different tenants coexists.
- [x] 1.4 Write RED tests for `Asignacion`: `usuario_id`, `rol_id`, optional context FKs, `responsable_id`, date range, soft delete.
- [x] 1.5 Implement `Asignacion` model with tenant-scoped FKs to `Usuario`, `Rol`, `Carrera`, `Cohorte`, `Materia`.
- [x] 1.6 Create Alembic migration `005_usuarios_asignaciones.py` with tables, constraints, indexes, and idempotent permission seed.
- [x] 1.7 Test migration upgrade/downgrade and idempotent seed of `usuarios:gestionar` and `equipos:asignar`.

## 2. Encryption and PII handling

- [x] 2.1 Write RED tests proving persisted `email`, `dni`, `cuil`, `cbu`, `alias_cbu` are not plaintext.
- [x] 2.2 Implement service-level encryption/decryption helpers using existing AES-256 utility; never log plaintext or ciphertext payloads.
- [x] 2.3 Add tests that responses do not include sensitive encrypted storage fields (`*_encrypted`, `*_hash`).
- [x] 2.4 Add tests for controlled validation errors without leaking PII.

## 3. Repositories

- [x] 3.1 Write RED tests for `UsuarioRepository`: list/get only current tenant, get by normalized email hash, excludes soft-deleted records.
- [x] 3.2 Implement `UsuarioRepository` extending `TenantScopedRepository`.
- [x] 3.3 Write RED tests for `AsignacionRepository`: filters by usuario, rol, context and active date range within tenant.
- [x] 3.4 Implement `AsignacionRepository` with `list_vigentes_for_user` and context filters.
- [x] 3.5 Triangulate cross-tenant context IDs: IDs from another tenant are invisible/fail closed.

## 4. Schemas

- [x] 4.1 Create `backend/app/schemas/usuarios.py` for `UsuarioCreate`, `UsuarioUpdate`, `UsuarioResponse`; all with `ConfigDict(extra='forbid')`.
- [x] 4.2 Add schema tests: body with `tenant_id`, `id`, `email_hash` or `*_encrypted` is rejected.
- [x] 4.3 Add `AsignacionCreate`, `AsignacionUpdate`, `AsignacionResponse` with derived `estado_vigencia`.
- [x] 4.4 Test date validation: `hasta < desde` rejects with 422.

## 5. Services

- [x] 5.1 Write RED tests for `UsuarioService.crear_usuario`: encrypts PII, computes email hash, rejects duplicate email per tenant with 409.
- [x] 5.2 Implement CRUD methods for usuarios; `DELETE` performs soft delete.
- [x] 5.3 Write RED tests for `AsignacionService.crear_asignacion`: validates same-tenant `usuario`, `rol`, context FKs and `responsable_id`.
- [x] 5.4 Implement CRUD methods for asignaciones and derived vigencia calculation.
- [x] 5.5 Triangulate vencida assignment: remains listable as historical but is not returned by active-permission query.

## 6. Routers / endpoints

- [x] 6.1 Create `backend/app/api/v1/routers/usuarios.py` with `/api/admin/usuarios` CRUD guarded by `require_permission("usuarios:gestionar")`.
- [x] 6.2 Endpoint tests: unauthenticated → 401; without permission → 403; with ADMIN permission can create/list/update/soft-delete users.
- [x] 6.3 Add `/api/asignaciones` CRUD guarded by `require_permission("equipos:asignar")`.
- [x] 6.4 Endpoint tests: assignment CRUD, filtering by usuario/rol/context, tenant isolation, vencida state in response.
- [x] 6.5 Register routers in API registry.

## 7. RBAC effective permissions

- [x] 7.1 Write RED test: a user with only a vencida assignment does not receive context-derived permissions.
- [x] 7.2 Update permission resolution to consider active assignments where required while preserving fail-closed behavior.
- [x] 7.3 Triangulate multi-role active assignments: permissions are unioned without duplicates.
- [x] 7.4 Verify existing RBAC tests still pass and global/admin behavior is unchanged.

## 8. Coverage and documentation

- [x] 8.1 Run targeted tests for usuarios/asignaciones and RBAC resolver.
- [x] 8.2 Run full backend test suite when explicitly authorized by orchestrator/user.
- [x] 8.3 Update `backend/app/models/__init__.py`, repositories exports and any OpenSpec spec deltas if implementation discovers a needed adjustment.
- [x] 8.4 After implementation and verification, mark C-07 in `CHANGES.md` and archive the change.
