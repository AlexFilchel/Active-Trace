## Verification Report

**Change**: comunicaciones-cola-worker
**Version**: N/A

---

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 24 |
| Tasks complete | 24 |
| Tasks incomplete | 0 |

All tasks remain marked complete in `tasks.md`.

---

### Build & Tests Execution

**Build**: ➖ Skipped

- Not run. `AGENTS.md` forbids build/compile/bundle without explicit user request.
- `openspec/config.yaml` is absent, so there is no verify override for build/type-check.

**Tests**: ✅ Passed

- `pytest tests/test_comunicaciones_tdd.py -q -k "preview_autorizado_profesor_retorna_200 or service_preview_resuelve_materia_fixture_valida or preview_personaliza_y_enqueue_exige_preview"`
  - Result: 3 passed / 0 failed / 20 deselected
- `pytest tests/test_comunicaciones_tdd.py tests/test_comunicaciones_migration_tdd.py tests/test_comunicaciones_worker_main_tdd.py tests/test_rbac_permissions_tdd.py -q`
  - Result: 32 passed / 0 failed / 0 skipped
- `pytest tests/test_comunicaciones_tdd.py tests/test_comunicaciones_migration_tdd.py tests/test_comunicaciones_worker_main_tdd.py -q`
  - Result: 26 passed / 0 failed / 0 skipped

**Coverage**: ➖ Not configured

- No `openspec/config.yaml` verify threshold configured.

---

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Ciclo de vida | Worker inicia despacho de pendiente | `tests/test_comunicaciones_tdd.py > test_worker_transiciones_a_enviado_y_audit` | ✅ COMPLIANT |
| Ciclo de vida | Transición inválida desde enviado es rechazada | `tests/test_comunicaciones_tdd.py > test_transicion_invalida_desde_enviado_rechazada` | ✅ COMPLIANT |
| Ciclo de vida | Cancelación solo desde pendiente | `tests/test_comunicaciones_tdd.py > test_cancelacion_solo_desde_pendiente` | ✅ COMPLIANT |
| Ciclo de vida | Cancelación durante envío es rechazada | `tests/test_comunicaciones_tdd.py > test_cancelacion_enviando_rechazada` | ✅ COMPLIANT |
| Preview obligatorio | Preview personaliza el contenido | `tests/test_comunicaciones_tdd.py > test_preview_personaliza_y_enqueue_exige_preview` | ✅ COMPLIANT |
| Preview obligatorio | Enqueue sin preview falla | `tests/test_comunicaciones_tdd.py > test_preview_personaliza_y_enqueue_exige_preview` | ✅ COMPLIANT |
| Enqueue masivo | Envío masivo crea lote | `tests/test_comunicaciones_tdd.py > test_enqueue_masivo_crea_lote_e_idempotencia` | ✅ COMPLIANT |
| Enqueue masivo | Reintento idempotente no duplica | `tests/test_comunicaciones_tdd.py > test_enqueue_masivo_crea_lote_e_idempotencia` | ✅ COMPLIANT |
| Enqueue masivo | Tenant isolation en enqueue | `tests/test_comunicaciones_tdd.py > test_enqueue_no_filtra_destinatario_otro_tenant` | ✅ COMPLIANT |
| Aprobación configurable | Lote requiere aprobación antes del worker | `tests/test_comunicaciones_tdd.py > test_worker_bloqueado_hasta_aprobacion_por_tenant` | ✅ COMPLIANT |
| Aprobación configurable | Aprobación por lote habilita despacho | `tests/test_comunicaciones_tdd.py > test_aprobacion_por_lote_y_permiso_fail_closed` | ✅ COMPLIANT |
| Aprobación configurable | Aprobación individual habilita solo un destinatario | `tests/test_comunicaciones_tdd.py > test_aprobacion_individual_habilita_solo_una` | ✅ COMPLIANT |
| Aprobación configurable | Usuario sin permiso no aprueba | `tests/test_comunicaciones_tdd.py > test_aprobacion_por_lote_y_permiso_fail_closed` | ✅ COMPLIANT |
| APIs seguras | Usuario con permiso genera preview | `tests/test_comunicaciones_tdd.py > test_preview_autorizado_profesor_retorna_200` | ✅ COMPLIANT |
| APIs seguras | Usuario sin permiso recibe 403 | `tests/test_comunicaciones_tdd.py > test_preview_sin_permiso_retorna_403` | ✅ COMPLIANT |
| APIs seguras | Body no puede suplantar identidad | `tests/test_comunicaciones_tdd.py > test_preview_rechaza_campos_extra_y_no_suplantacion_identidad` | ✅ COMPLIANT |
| Worker idempotente | Worker procesa pendiente aprobada con éxito | `tests/test_comunicaciones_tdd.py > test_worker_transiciones_a_enviado_y_audit` | ✅ COMPLIANT |
| Worker idempotente | Worker registra error de proveedor | `tests/test_comunicaciones_tdd.py > test_worker_error_controlado_sin_pii_en_logs` | ✅ COMPLIANT |
| Worker idempotente | Worker no envía canceladas | `tests/test_comunicaciones_tdd.py > test_worker_omite_canceladas` | ✅ COMPLIANT |
| Auditoría | Enqueue audita comunicación enviar | `tests/test_comunicaciones_tdd.py > test_worker_transiciones_a_enviado_y_audit` | ✅ COMPLIANT |
| Auditoría | Aprobación audita aprobación | `tests/test_comunicaciones_tdd.py > test_worker_bloqueado_hasta_aprobacion_por_tenant` | ✅ COMPLIANT |
| Auditoría | Cancelación audita cancelación | `tests/test_comunicaciones_tdd.py > test_cancelacion_audita_sin_plaintext` | ✅ COMPLIANT |
| RBAC | Permiso comunicacion enviar existe por tenant | `tests/test_comunicaciones_migration_tdd.py > test_comunicaciones_migration_crea_tabla_y_seed` | ✅ COMPLIANT |
| RBAC | Permiso comunicacion aprobar existe por tenant | `tests/test_comunicaciones_migration_tdd.py > test_comunicaciones_migration_crea_tabla_y_seed` | ✅ COMPLIANT |
| RBAC | Endpoint de aprobación falla cerrado | `tests/test_comunicaciones_tdd.py > test_aprobacion_por_lote_y_permiso_fail_closed` | ✅ COMPLIANT |
| Encrypted at rest | Destinatario persistido no es plaintext | `tests/test_comunicaciones_tdd.py > test_encrypta_destinatario_y_mascara_api` | ✅ COMPLIANT |
| Encrypted at rest | API no devuelve destinatario completo | `tests/test_comunicaciones_tdd.py > test_encrypta_destinatario_y_mascara_api` | ✅ COMPLIANT |
| Encrypted at rest | Logs no contienen destinatario plaintext | `tests/test_comunicaciones_tdd.py > test_worker_error_controlado_sin_pii_en_logs` | ✅ COMPLIANT |

**Compliance summary**: 28/28 scenarios compliant

---

### Correctness (Static — Structural Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| State machine exacta | ✅ Implemented | `_ALLOWED_STATES` matches spec exactly and rejects invalid transitions centrally in services. |
| Preview token required | ✅ Implemented | Enqueue validates preview token tied to actor, tenant, materia, templates, destinatarios y expiración. |
| Enqueue idempotency by lote | ✅ Implemented | Repository reuses rows by `tenant_id + idempotency_key`. |
| Tenant isolation | ✅ Implemented | `get_materia()` and `list_entries()` stay tenant-scoped in repository. |
| Approval configurable per tenant | ✅ Implemented | Tenant policy is read server-side and massive ambiguity resolves fail-safe. |
| RBAC fail-closed | ✅ Implemented | Router uses `require_permission("comunicacion:enviar")` and `require_permission("comunicacion:aprobar")`. |
| Identity only from session | ✅ Implemented | DTOs forbid extra fields and service identity comes from `AuthenticatedUser`. |
| Recipient encrypted at rest | ✅ Implemented | Model persists `destinatario_encrypted`; API returns masked representation only. |
| No plaintext in audit/logs | ✅ Implemented | Audit payloads and worker logs use ids/counts, not recipient plaintext. |
| Worker retry/idempotency safety | ✅ Implemented | Dispatch uses `skip_locked`, stable provider idempotency key, retry accounting, and terminal `Error`. |
| Queries only in repositories | ✅ Implemented | Routers call services; services depend on repositories for data access. |

---

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Cola DB-backed inicial | ✅ Yes | Queue remains DB-backed with repository selection and row locking. |
| State machine en services | ✅ Yes | Transition guards live in services, not routers. |
| Aprobación como metadatos por fila/lote | ✅ Yes | `requiere_aprobacion`, `aprobado_*`, `cancelado_*`, `intentos`, `error_detalle` are used directly on rows. |
| Preview token/huella | ✅ Yes | HMAC preview token binds actor/tenant/request shape. |
| Side effects after transition | ✅ Yes | Worker moves to `Enviando` before provider call. |
| Tenant config fail-safe | ✅ Yes | Approval policy fallback remains conservative for ambiguous massive sends. |
| File changes plan | ✅ Yes | Expected backend model/schema/repository/service/router/worker files are present and wired. |

---

### Issues Found

**CRITICAL** (must fix before archive):
None

**WARNING** (should fix):

1. Build/type-check remains intentionally unverified because `AGENTS.md` forbids build execution without explicit user request.
2. Historical RBAC seed still contains legacy permission name `comunicacion:aprobar_masiva` in `backend/alembic/versions/003_rbac.py`; C-12 runtime path uses `comunicacion:aprobar`, so current change passes, but old migration history still carries catalog drift.

**SUGGESTION** (nice to have):
None

---

### Verdict
PASS CON OBSERVACIONES

Runtime regressions are resolved, core comunicaciones suites are green, OpenSpec validation passes, and no critical spec/design gaps remain; implementation is complete for this change, with only non-blocking observations left.
