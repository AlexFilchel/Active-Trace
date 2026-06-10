## Context

C-01–C-05 están completos y archivados. El proyecto tiene: FastAPI skeleton, SQLAlchemy 2.0 async con `TenantScopedMixin` + soft delete, Alembic con tres migraciones (tenant, auth, rbac), RBAC con `require_permission()` guard y audit log. No hay ninguna entidad del dominio académico. Este change introduce el catálogo base: `Carrera`, `Cohorte`, `Materia`.

Restricciones activas:
- Cada entidad hereda `TenantScopedMixin` (id UUID, tenant_id, created_at, updated_at, deleted_at)
- Soft delete obligatorio: `DELETE` = `deleted_at = now()`, no hard delete
- Todo query pasa por Repository con scope de tenant activo por defecto
- Guard `require_permission("estructura:gestionar")` en todos los endpoints de escritura
- Strict TDD: test falla → código mínimo → triangulación → refactor

## Goals / Non-Goals

**Goals:**
- Modelos `Carrera`, `Cohorte`, `Materia` con `TenantScopedMixin`, unicidades y soft delete
- Migración `004_estructura_academica` con tablas + constraints + índices
- Endpoints ABM REST: `/api/admin/carreras`, `/api/admin/cohortes`, `/api/admin/materias`
- Schemas Pydantic v2 (`extra='forbid'`) para request/response de las tres entidades
- Guard `estructura:gestionar` con seed del permiso en rol ADMIN en la migración 004
- Regla de negocio: carrera inactiva no admite nuevas cohortes en estado Activa
- Suite TDD: CRUD, unicidades, aislamiento multi-tenant, reglas de estado

**Non-Goals:**
- Entidad `Dictado` (instancia Materia × Carrera × Cohorte) — ADR-006 la define pero se implementa en changes posteriores cuando se necesite como contexto para calificaciones o equipos
- Entidad `Asignacion` (Usuario ↔ Rol ↔ contexto académico) — C-07
- `ProgramaMateria` y `FechaAcademica` — C-17
- Endpoints de lectura pública para alumnos/docentes — C-07 en adelante
- Frontend — C-21 en adelante

## Decisions

### D-01: Módulo único `estructura` para las tres entidades

**Decisión**: Un solo módulo `estructura.py` para `Carrera`, `Cohorte`, `Materia` — no tres archivos separados.

**Alternativa considerada**: un archivo por entidad (`carrera.py`, `cohorte.py`, `materia.py`).

**Rationale**: Las tres entidades forman un catálogo cohesivo del tenant. Son simples (3–5 campos), tienen el mismo guard, el mismo patrón de repositorio y no hay lógica de negocio compleja entre ellas. Dividirlas sería fragmentación prematura. La regla de ≤500 LOC/archivo se cumple holgadamente con un solo archivo.

---

### D-02: Seed del permiso `estructura:gestionar` en migración 004

**Decisión**: El permiso `estructura:gestionar` se siembra en la migración `004_estructura_academica`, no en `003_rbac`.

**Alternativa considerada**: modificar la migración 003 o agregar una migración 004b dedicada al seed.

**Rationale**: Cada change agrega su propio seed de permisos en su propia migración. Modificar una migración ya ejecutada (003) viola el contrato de Alembic. Una migración por cambio de schema y de seed es el patrón establecido en el proyecto. La migración 004 hace todo: crea las tablas Y siembra el permiso en todos los tenants existentes con `INSERT ... ON CONFLICT DO NOTHING`.

---

### D-03: Regla de negocio en Service, no en DB constraint

**Decisión**: La regla "carrera inactiva no admite nuevas cohortes en estado Activa" se valida en el Service layer con HTTP 422, no como constraint de DB.

**Alternativa considerada**: trigger o check constraint en PostgreSQL.

**Rationale**: Los constraints de DB son difíciles de testear en aislamiento (requieren una transacción real), producen errores crípticos difíciles de mapear a respuestas HTTP, y complican las migraciones cuando la regla cambia. El Service es el lugar correcto para reglas de negocio según el patrón Clean Architecture del proyecto. El constraint de unicidad `(tenant_id, codigo)` SÍ va en DB porque es integridad referencial, no una regla de negocio mutable.

---

### D-04: Estado como columna string con validación Pydantic (no ENUM PostgreSQL)

**Decisión**: `estado` se almacena como `String(20)` en PostgreSQL, no como `ENUM` nativo de Postgres.

**Alternativa considerada**: `Enum('Activa', 'Inactiva', name='estado_carrera')` como tipo nativo PostgreSQL.

**Rationale**: Los ENUM de PostgreSQL requieren una migración de `ALTER TYPE` para agregar valores, lo que complica el ciclo de cambios. El patrón del proyecto (ver modelos existentes en C-02/C-04) usa strings con validación en el schema Pydantic. El check de integridad se hace en Python, no en el motor. El impacto en performance es negligible para una columna de configuración administrativa.

---

### D-05: Soft delete con `deleted_at` — listados filtran automáticamente

**Decisión**: El `BaseRepository` ya filtra `deleted_at IS NULL` en todos los queries. Los endpoints de `DELETE` ejecutan soft delete (patch a `deleted_at`), no hard delete.

**Rationale**: Patrón ya establecido en C-02 (`TenantScopedMixin`). La auditoría append-only (C-05) requiere que los registros nunca desaparezcan. Consistencia con todo el stack.

## Risks / Trade-offs

- [Risk] Una cohorte puede quedar "huérfana" si se inactiva su carrera luego de crearla → La inactivación de carrera no cambia el estado de cohortes existentes; se valida solo al CREAR nuevas cohortes. Aceptado — las cohortes históricas deben preservarse.

- [Risk] El `TenantScopedMixin` asume que el `tenant_id` viene del JWT. Si se pasa un `tenant_id` distinto en el body, se ignora → Este es el comportamiento correcto según Regla Dura #8. El router extrae el tenant del `current_user` dependency. El schema Pydantic no expone `tenant_id` en el request body.

- [Risk] PA-01 y PA-07 aún aparecen como "abiertas" en `knowledge-base/10_preguntas_abiertas.md`, pero ambas están resueltas por el modelo de datos y ADR-006 → Actualizar la KB después de este change (`Cohorte.carrera_id` responde PA-07; ADR-006 responde PA-01). No bloquea la implementación.

## Migration Plan

1. `alembic upgrade 004_estructura_academica`: crea tablas `carrera`, `cohorte`, `materia` + constraints + siembra `estructura:gestionar` en ADMIN
2. No hay rollback de datos (las tablas son nuevas); el downgrade elimina las tablas
3. Despliegue sin downtime: las tablas nuevas no afectan los endpoints existentes
4. El seed es idempotente (`INSERT ... ON CONFLICT DO NOTHING`) — seguro re-ejecutar

## Open Questions

- PA-01 y PA-07 están resueltas implícitamente por el modelo; deben marcarse como cerradas en `10_preguntas_abiertas.md` post-implementación
- ¿`Cohorte.anio` es obligatorio o puede inferirse de `vig_desde`? → Por ahora obligatorio; es un atributo de negocio explícito (ej. cohorte MAR-2026 tiene anio=2026)
