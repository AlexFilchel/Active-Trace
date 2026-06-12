## Verification Report

**Change**: c-07-usuarios-y-asignaciones
**Mode**: openspec

---

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 38 |
| Tasks complete | 37 |
| Tasks incomplete | 1 |

Incomplete tasks:
- 8.4 After implementation and verification, mark C-07 in `CHANGES.md` and archive the change.

Assessment:
- 8.4 is expected to remain pending during verify; it does not block verification.

---

### Evidence Checked
- Change artifacts:
  - `openspec/changes/c-07-usuarios-y-asignaciones/proposal.md`
  - `openspec/changes/c-07-usuarios-y-asignaciones/design.md`
  - `openspec/changes/c-07-usuarios-y-asignaciones/tasks.md`
  - `openspec/changes/c-07-usuarios-y-asignaciones/specs/usuarios-y-asignaciones/spec.md`
- Implementation:
  - `backend/app/models/usuarios.py`
  - `backend/app/repositories/usuarios.py`
  - `backend/app/repositories/rbac.py`
  - `backend/app/services/usuarios.py`
  - `backend/app/schemas/usuarios.py`
  - `backend/app/api/v1/routers/usuarios.py`
  - `backend/app/core/permissions.py`
  - `backend/app/main.py`
  - `backend/alembic/versions/005_usuarios_asignaciones.py`
- Tests inspected:
  - `backend/tests/test_usuarios_models_tdd.py`
  - `backend/tests/test_usuarios_repositories_tdd.py`
  - `backend/tests/test_usuarios_schemas_tdd.py`
  - `backend/tests/test_usuarios_service_tdd.py`
  - `backend/tests/test_usuarios_endpoints_tdd.py`
  - `backend/tests/test_usuarios_migration_tdd.py`
  - `backend/tests/test_rbac_assignment_permissions_tdd.py`

---

### Tests Run

**Targeted change tests**: ✅ Passed

Command:
```bash
pytest tests/test_usuarios_models_tdd.py tests/test_usuarios_repositories_tdd.py tests/test_usuarios_schemas_tdd.py tests/test_usuarios_service_tdd.py tests/test_usuarios_endpoints_tdd.py tests/test_usuarios_migration_tdd.py tests/test_rbac_assignment_permissions_tdd.py
```

Result: **19 passed / 0 failed / 0 skipped**

**Full backend suite**: ✅ Passed

Command:
```bash
pytest
```

Result: **158 passed / 0 failed / 0 skipped**

**Build/type-check**: Not run.
- No `openspec/config.yaml` verify command is present in the repo.
- `AGENTS.md` forbids build/compile without explicit user request.

**Coverage threshold**: Not configured.

---

### Spec Compliance Matrix

| Requirement | Scenario | Runtime evidence | Result |
|-------------|----------|------------------|--------|
| Modelo Usuario con PII cifrada y aislamiento tenant | PII no se persiste como plaintext | `test_usuarios_service_tdd.py::test_crear_usuario_encrypts_pii_and_rejects_duplicate_email` | ✅ COMPLIANT |
| Modelo Usuario con PII cifrada y aislamiento tenant | Unicidad de email por tenant con email cifrado | `test_usuarios_service_tdd.py::test_crear_usuario_encrypts_pii_and_rejects_duplicate_email` and `test_usuarios_models_tdd.py::test_usuario_email_hash_unique_per_tenant` | ✅ COMPLIANT |
| Modelo Usuario con PII cifrada y aislamiento tenant | Mismo email en tenants distintos coexiste | `test_usuarios_models_tdd.py::test_usuario_email_hash_unique_per_tenant` | ✅ COMPLIANT |
| Modelo Usuario con PII cifrada y aislamiento tenant | Legajo no actúa como identidad de sesión | `test_usuarios_endpoints_tdd.py::test_request_business_identifiers_do_not_override_session_identity` | ✅ COMPLIANT |
| Modelo Asignacion con rol, contexto académico y vigencia temporal | Asignacion vigente es identificada por rango de fechas | `test_usuarios_models_tdd.py::test_asignacion_model_context_and_vigencia` and `test_usuarios_endpoints_tdd.py::test_asignaciones_endpoints_guard_tenant_isolation_and_vigencia_state` | ✅ COMPLIANT |
| Modelo Asignacion con rol, contexto académico y vigencia temporal | Asignacion vencida conserva histórico | `test_usuarios_service_tdd.py::test_crear_asignacion_validates_same_tenant_and_historical_listing` and `test_rbac_assignment_permissions_tdd.py::test_vencida_assignment_does_not_grant_effective_permissions` | ✅ COMPLIANT |
| Modelo Asignacion con rol, contexto académico y vigencia temporal | Contexto académico debe pertenecer al mismo tenant | `test_usuarios_service_tdd.py::test_crear_asignacion_validates_same_tenant_and_historical_listing` and `test_usuarios_endpoints_tdd.py::test_asignaciones_endpoints_reject_foreign_tenant_context_and_responsable` | ✅ COMPLIANT |
| Modelo Asignacion con rol, contexto académico y vigencia temporal | Responsable debe pertenecer al mismo tenant | `test_usuarios_service_tdd.py::test_crear_asignacion_validates_same_tenant_and_historical_listing` and `test_usuarios_endpoints_tdd.py::test_asignaciones_endpoints_reject_foreign_tenant_context_and_responsable` | ✅ COMPLIANT |
| ABM de usuarios protegido por permiso usuarios:gestionar | Crear usuario con permiso devuelve 201 | `test_usuarios_endpoints_tdd.py::test_usuarios_endpoints_guard_and_filter_sensitive_fields` | ✅ COMPLIANT |
| ABM de usuarios protegido por permiso usuarios:gestionar | Usuario sin permiso recibe 403 | `test_usuarios_endpoints_tdd.py::test_usuarios_endpoints_guard_and_filter_sensitive_fields` | ✅ COMPLIANT |
| ABM de usuarios protegido por permiso usuarios:gestionar | Listado de usuarios respeta tenant | `test_usuarios_endpoints_tdd.py::test_usuarios_endpoints_guard_and_filter_sensitive_fields` and tenant-scoped repository coverage | ✅ COMPLIANT |
| CRUD de asignaciones protegido por permiso equipos:asignar | Crear asignacion con contexto válido devuelve 201 | `test_usuarios_endpoints_tdd.py::test_asignaciones_endpoints_guard_tenant_isolation_and_vigencia_state` | ✅ COMPLIANT |
| CRUD de asignaciones protegido por permiso equipos:asignar | Listado soporta filtros por usuario, rol y contexto | `test_usuarios_repositories_tdd.py::test_asignacion_repository_filters_context_and_vigencia` and `test_usuarios_endpoints_tdd.py::test_asignaciones_endpoints_guard_tenant_isolation_and_vigencia_state` | ✅ COMPLIANT |
| CRUD de asignaciones protegido por permiso equipos:asignar | Soft delete de asignacion preserva histórico | `test_usuarios_endpoints_tdd.py::test_asignaciones_endpoints_support_get_patch_delete_and_hide_soft_deleted_by_default` | ✅ COMPLIANT |
| Permisos efectivos consideran vigencia de asignaciones | Asignacion vencida no autoriza | `test_rbac_assignment_permissions_tdd.py::test_vencida_assignment_does_not_grant_effective_permissions` | ✅ COMPLIANT |
| Permisos efectivos consideran vigencia de asignaciones | Multiples asignaciones vigentes unionan permisos | `test_rbac_assignment_permissions_tdd.py::test_active_multi_role_assignments_union_permissions_without_duplicates` | ✅ COMPLIANT |
| Permisos efectivos consideran vigencia de asignaciones | Tenant ajeno no aporta permisos | `test_usuarios_service_tdd.py::test_crear_asignacion_validates_same_tenant_and_historical_listing` plus tenant-scoped repository/endpoint rejection coverage | ✅ COMPLIANT |
| Schemas Pydantic v2 rechazan campos no declarados | Request con tenant_id es rechazado | `test_usuarios_schemas_tdd.py::test_usuario_schemas_forbid_internal_fields_and_tenant_id` and endpoint 422 coverage in `test_usuarios_endpoints_tdd.py::test_usuarios_endpoints_guard_and_filter_sensitive_fields` | ✅ COMPLIANT |
| Schemas Pydantic v2 rechazan campos no declarados | Request con campos internos de cifrado es rechazado | `test_usuarios_schemas_tdd.py::test_usuario_schemas_forbid_internal_fields_and_tenant_id` | ✅ COMPLIANT |
| Schemas Pydantic v2 rechazan campos no declarados | Fechas inválidas son rechazadas | `test_usuarios_schemas_tdd.py::test_asignacion_schema_rejects_invalid_dates` | ✅ COMPLIANT |
| Migracion 005 crea usuarios, asignaciones y permisos base | Migracion crea tablas requeridas | `test_usuarios_migration_tdd.py::test_migration_005_creates_usuario_and_asignacion_and_is_idempotent` | ✅ COMPLIANT |
| Migracion 005 crea usuarios, asignaciones y permisos base | Seed de permisos es idempotente | `test_usuarios_migration_tdd.py::test_migration_005_creates_usuario_and_asignacion_and_is_idempotent` | ✅ COMPLIANT |
| Migracion 005 crea usuarios, asignaciones y permisos base | Roles esperados reciben permisos | `test_usuarios_migration_tdd.py::test_migration_005_creates_usuario_and_asignacion_and_is_idempotent` | ✅ COMPLIANT |

**Compliance summary**: **23/23 scenarios compliant**

---

### Correctness / Design Coherence

Matches design:
- `Usuario` remains separate from `AuthUser` and tenant-scoped.
- Email uses encrypted storage plus `email_hash` uniqueness.
- `Asignacion.rol_id` references `rol.id`.
- `estado_vigencia` is derived and not persisted.
- Services validate same-tenant context and `responsable_id` through tenant-scoped repositories.
- Routers use permission guards and are registered in `backend/app/main.py`.
- RBAC resolution unions JWT-role permissions with active assignment permissions only.

Observed design alignment updates since previous verify:
- The partial unique index for `(tenant_id, legajo)` when present is implemented in both model and migration.
- Migration downgrade now removes seeded `permiso` / `rol_permiso` rows before dropping tables, matching the design plan.

---

### Issues Found

**CRITICAL**
- None.

**WARNING**
- Build/type-check was not executed because no verify build command is configured and `AGENTS.md` forbids running build commands without explicit request.

**SUGGESTION**
- Add `openspec/config.yaml` verify commands if the project wants build/type-check enforced as part of future verify passes.

---

### Verdict
**PASS WITH NOTES**

The previously failing/full-suite and scenario-evidence gaps are closed. C-07 now satisfies the delta spec, matches the design intent, has task evidence consistent with the implementation, and the backend suite is green. The only remaining note is operational: archive step 8.4 is still pending, so the change is ready for archive.
