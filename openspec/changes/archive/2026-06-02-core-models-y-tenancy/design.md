## Context

activia-trace ya tiene app FastAPI, SQLAlchemy async y Alembic inicializados por C-01, pero `core/tenancy.py`, `models/`, `repositories/` y el baseline de dominio siguen vacíos. C-02 es el primer change crítico del roadmap: debe convertir ADR-002 (row-level multi-tenancy) y las reglas duras de `AGENTS.md` en contrato técnico ejecutable, sin tocar auth todavía.

## Goals / Non-Goals

**Goals:**

- Introducir `Tenant` como raíz persistente del sistema.
- Definir convenciones ORM reutilizables para UUID interno, timestamps y soft delete.
- Forzar scope de tenant en repositories como comportamiento por defecto y fail-closed.
- Dejar lista la utilidad AES-256 para futuros campos `[cifrado]`.
- Crear la migración `001_tenant` y fijar convención de migración secuencial.
- Dejar aceptación clara para tests de aislamiento, soft delete, cifrado y lifecycle.

**Non-Goals:**

- JWT, identidad de request o `get_current_user` (C-03).
- RBAC y `require_permission` (C-04).
- Modelos académicos (`Carrera`, `Materia`, `Usuario`) y uso real de PII cifrada (C-06/C-07).
- UI, endpoints de negocio o seeds funcionales más allá de lo mínimo para `Tenant`.

## Decisions

### D1 — Separar lifecycle base de scope tenant

Se usarán dos piezas composables en vez de un único mixin monolítico:

- `UuidLifecycleMixin`: `id`, `created_at`, `updated_at`, `deleted_at`.
- `TenantScopedMixin`: hereda lifecycle y agrega `tenant_id` + FK a `Tenant`.

Rationale: el roadmap exige que toda entidad de negocio tenga `tenant_id`, pero la propia raíz `Tenant` no puede autorreferenciarse como tenant-scoped. Separar ambas capas preserva el contrato sin introducir una incoherencia estructural.

Alternativa descartada: poner `tenant_id` también en `Tenant` con semántica especial. Se descarta por ambigua y por romper la legibilidad del modelo.

### D2 — Repository base con tenant obligatorio y fail-closed

El repository genérico deberá construirse/instanciarse con `tenant_id` explícito. Sin ese contexto, no operará. Todas las lecturas filtrarán por `tenant_id` y excluirán `deleted_at IS NOT NULL` por defecto. El borrado del repository será lógico (setea `deleted_at`) y no físico.

Rationale: la regla dura del proyecto dice que un query sin scope es un bug de review. Volver el scope obligatorio en la API del repository hace que el error ocurra antes, en el diseño, no solo en revisión humana.

Alternativas descartadas:
- Inyectar tenant opcional y confiar en cada método → demasiado fácil de omitir.
- Resolver tenant desde globals/request-local → C-02 no debe acoplar persistencia a HTTP/auth.

### D3 — Soft delete transversal, con inclusión explícita solo para casos administrativos

El contrato base será:

- consultas normales: excluyen borrados;
- acceso a borrados: opt-in explícito;
- delete: marca timestamp;
- restore/hard-delete: fuera de scope de C-02.

Rationale: coincide con auditoría append-only y evita que futuros módulos reinterpreten el borrado como hard delete.

### D4 — Utilidad AES-256 en `core/security.py` como contrato compartido

Aunque `core/security.py` fue reservado en C-01 para C-03, C-02 implementará ahí la parte transversal de cifrado en reposo: una API pequeña para `encrypt_value`/`decrypt_value`, basada en `ENCRYPTION_KEY`, reusable por modelos/repositorios futuros.

Recomendación de implementación para apply: usar cifrado autenticado AES-256 (p. ej. GCM) mediante una librería mantenida, y definir un formato de payload versionado para permitir rotación futura.

Rationale: el cifrado at-rest es una preocupación transversal previa a `Usuario`; postergarlo a C-07 haría que el contrato crítico llegue tarde.

Alternativa descartada: resolver cifrado recién al modelar `Usuario`. Se descarta porque el roadmap pide probar round-trip y fijar la utilidad ahora.

### D5 — Migración `001_tenant` mínima pero canónica

La primera migración de dominio creará `tenant` con UUID y lifecycle base, y dejará fijada la convención:

- revisions secuenciales con prefijo de tres dígitos (`001_*`, `002_*`, ...);
- una migración por cambio de schema;
- metadata ORM centralizada para autogenerate consistente.

Rationale: C-02 debe abrir el carril de migraciones antes de auth y RBAC. La tabla `tenant` es suficiente para anclar FKs futuras sin adelantar entidades fuera de scope.

## Risks / Trade-offs

- **[El alcance menciona “mixin con tenant_id” pero `Tenant` no puede usarlo tal cual]** → Mitigación: formalizar la separación `UuidLifecycleMixin` / `TenantScopedMixin` en proposal + specs.
- **[La utilidad AES agrega una dependencia criptográfica nueva]** → Mitigación: encapsularla en `core/security.py` con API mínima y tests de round-trip/wrong-key.
- **[Repository genérico demasiado abstracto puede volverse rígido]** → Mitigación: limitar C-02 al contrato base (scope tenant + soft delete + CRUD simple) y extender en changes futuros solo cuando haya casos reales.
- **[Soft delete transversal puede ocultar datos en debugging]** → Mitigación: exponer una vía explícita `include_deleted` para casos administrativos/test, nunca como default.

## Migration Plan

1. Crear metadata/modelos base y tabla `tenant`.
2. Generar/aplicar `001_tenant` en entorno local/test.
3. Implementar repository base y utilidad de cifrado.
4. Ejecutar tests de aislamiento multi-tenant, soft delete, round-trip de cifrado y timestamps.

Rollback: revertir la revisión `001_tenant` y eliminar el código transversal nuevo. Como solo introduce baseline de dominio y no hay módulos consumidores todavía, el rollback es acotado y auditable.

## Open Questions

- ¿El modelo `Tenant` necesita en C-02 solo identidad mínima (`id`, `name`, `slug`, `status`) o también configuración inicial? Recomendación: mantenerlo mínimo y dejar configuración por tenant para changes posteriores.
- La arquitectura exige `ENCRYPTION_KEY` de 32 chars; en apply habrá que fijar explícitamente la transformación string→32 bytes para evitar ambigüedad operativa.
