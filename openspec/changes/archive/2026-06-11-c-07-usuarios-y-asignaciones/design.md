## Context

C-01–C-06 están completos. Existen `TenantScopedMixin`, cifrado AES-256, auth JWT (`AuthUser`), RBAC (`Rol`, `Permiso`, `RolPermiso`), audit log y estructura académica (`Carrera`, `Cohorte`, `Materia`). C-07 agrega la identidad de dominio (`Usuario`) y la asignación contextual temporal (`Asignacion`).

Restricciones activas:
- Identidad y tenant siempre desde JWT verificado; nunca desde request.
- Toda tabla lleva `tenant_id`; todo repository filtra por tenant por defecto.
- PII sensible cifrada en reposo y ausente de logs.
- Soft delete obligatorio.
- Routers → Services → Repositories → Models.
- Pydantic v2 `extra='forbid'`.
- Strict TDD.

## Goals / Non-Goals

**Goals:**
- Modelar `Usuario` como perfil de dominio del tenant, separado de la cuenta técnica `AuthUser`.
- Modelar `Asignacion` como vínculo Usuario ↔ Rol ↔ contexto académico con vigencia.
- Enforcear unicidad `(tenant_id, email_hash)` sin guardar email plaintext.
- Exponer ABM usuarios y CRUD asignaciones con permisos finos.
- Hacer que asignaciones vencidas no otorguen permisos contextuales.
- Preservar histórico de asignaciones vencidas o soft-deleted.

**Non-Goals:**
- Frontend de usuarios/equipos.
- Asignación masiva, clonado y exportación de equipos — C-08.
- Padrón de alumnos — C-09.
- Liquidaciones — C-18.
- Definir semántica completa de NEXO — queda acotado a rol asignable; PA-25 sigue abierta para permisos de negocio futuros.

## Decisions

### D-01: `Usuario` de dominio separado de `AuthUser`

**Decisión**: `AuthUser` sigue siendo cuenta de autenticación; `Usuario` representa la persona/perfil operativo con PII, legajos, datos bancarios y estado. `Usuario.auth_user_id` será nullable y único por tenant para permitir usuarios sin login inicial.

**Rationale**: Evita mezclar credenciales/sesiones con datos personales y bancarios. También permite docentes o alumnos precargados antes de habilitarles acceso.

---

### D-02: Email cifrado + hash ciego para unicidad

**Decisión**: guardar `email_encrypted` y `email_hash` (HMAC/SHA-256 normalizado con clave de app) para unicidad `(tenant_id, email_hash)`. No se usa `email` plaintext en DB.

**Rationale**: La KB exige email cifrado y unicidad por tenant. El cifrado aleatorio no permite unique directo; el hash ciego resuelve búsqueda/unicidad sin exponer plaintext.

---

### D-03: `Asignacion.rol_id` referencia al catálogo `Rol`

**Decisión**: usar FK `rol_id` a `rol.id`, no string enum.

**Rationale**: C-04 definió roles administrables por tenant. Una FK evita drift entre asignaciones y catálogo RBAC, y permite roles personalizados.

---

### D-04: `estado_vigencia` derivado, no columna persistida

**Decisión**: calcular `Vigente | Vencida | Futura` desde `desde/hasta` en service/schema o propiedad de dominio; no persistirlo.

**Rationale**: Evita inconsistencias diarias y jobs de actualización. La regla de autorización consulta rango de fechas en DB.

---

### D-05: Contexto académico opcional pero tenant-consistente

**Decisión**: `materia_id`, `carrera_id`, `cohorte_id` son nullable para roles globales de tenant; si se informan, deben existir en el mismo tenant.

**Rationale**: ADMIN/FINANZAS pueden operar globalmente; docentes suelen estar acotados a materia/cohorte/comisiones.

## Data Model

`usuario`:
- `id`, `tenant_id`, timestamps, `deleted_at`
- `auth_user_id` nullable FK `auth_user.id`, unique
- `nombre`, `apellidos`, `email_encrypted`, `email_hash`, `dni_encrypted`, `cuil_encrypted`, `cbu_encrypted`, `alias_cbu_encrypted`
- `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador`, `estado`
- unique `(tenant_id, email_hash)` and optional `(tenant_id, legajo)` if legajo present

`asignacion`:
- `id`, `tenant_id`, timestamps, `deleted_at`
- `usuario_id` FK `usuario.id`, `rol_id` FK `rol.id`
- nullable context FKs: `materia_id`, `carrera_id`, `cohorte_id`
- `comisiones` JSONB list, `responsable_id` nullable FK `usuario.id`
- `desde` date, `hasta` nullable date
- indexes on `tenant_id`, `usuario_id`, `rol_id`, context FKs, date range

## API Sketch

- `GET/POST /api/admin/usuarios`
- `GET/PATCH/DELETE /api/admin/usuarios/{id}`
- `GET/POST /api/asignaciones`
- `GET/PATCH/DELETE /api/asignaciones/{id}`

Requests never accept `tenant_id`. Responses expose decrypted PII only to callers with `usuarios:gestionar`; otherwise use redacted fields in future read models.

## RBAC Integration

For C-07, global permissions may continue resolving from JWT role names + `RolPermiso`. Contextual checks must use active `Asignacion` rows: `desde <= today` and (`hasta IS NULL OR hasta >= today`), not soft-deleted, same tenant. A vencida assignment is historical only.

## Risks / Trade-offs

- [Risk] Introducing `Usuario` beside `AuthUser` can confuse identity boundaries → Mitigate with naming, docs and tests: auth identity is session, domain person is business data.
- [Risk] Email hash becomes sensitive lookup metadata → Use keyed HMAC, normalize email, never log hash with plaintext.
- [Risk] PA-25 NEXO unresolved → Keep NEXO assignable but avoid NEXO-specific behavior in C-07.
- [Risk] RBAC resolver changes are security-critical → TDD with fail-closed tests before implementation.

## Migration Plan

1. Create `usuario` and `asignacion` tables with tenant FKs, constraints and indexes.
2. Seed `usuarios:gestionar` for ADMIN and `equipos:asignar` for COORDINADOR/ADMIN idempotently.
3. No data backfill required; existing `auth_user` remains source for login.
4. Downgrade drops `asignacion` then `usuario` after removing seeded permissions/relations introduced by 005.

## Open Questions

- Whether every `AuthUser` must eventually have one `Usuario` profile can be enforced in a later migration once onboarding flow is defined.
- PA-25 remains open for NEXO business semantics; not blocking generic assignment storage.
