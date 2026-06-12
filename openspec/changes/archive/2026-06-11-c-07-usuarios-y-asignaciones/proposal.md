## Why

C-06 dejó listas las entidades raíz académicas (`Carrera`, `Cohorte`, `Materia`), pero el sistema todavía no tiene identidad de dominio ni asignaciones temporales por contexto. Sin `Usuario` y `Asignacion`, no se pueden construir equipos docentes, padrón, calificaciones, encuentros, liquidaciones ni permisos contextuales. C-07 introduce la persona operativa del tenant, PII cifrada y el vínculo Usuario ↔ Rol ↔ contexto académico con vigencia histórica.

## What Changes

- Nuevo modelo `Usuario` como perfil/persona de dominio, tenant-scoped y soft-delete, vinculado 1:1 opcionalmente con `auth_user` para login.
- PII cifrada en reposo: `email`, `dni`, `cuil`, `cbu`, `alias_cbu`; nunca plaintext en DB, logs ni responses no autorizadas.
- Nuevo modelo `Asignacion` con `usuario_id`, `rol_id`, contexto opcional (`materia_id`, `carrera_id`, `cohorte_id`), `comisiones` JSONB/lista, `responsable_id`, `desde`, `hasta` y `estado_vigencia` derivado.
- Migración Alembic `005_usuarios_asignaciones`: tablas, constraints, índices y seed idempotente de permisos `usuarios:gestionar` y `equipos:asignar`.
- Endpoints ABM usuarios bajo `/api/admin/usuarios` con guard `usuarios:gestionar`.
- Endpoints CRUD asignaciones bajo `/api/asignaciones` con guard `equipos:asignar`.
- Integración del resolvedor RBAC para que asignaciones vencidas no otorguen permisos efectivos.
- Schemas Pydantic v2 con `extra='forbid'`; `tenant_id` e identidad autenticada nunca aceptados desde body.
- Suite TDD para cifrado PII, unicidad email por tenant, vigencia, multi-rol, jerarquía responsable y aislamiento multi-tenant.

## Capabilities

### New Capabilities
- `usuarios-y-asignaciones`: gestión administrativa de usuarios/personas del tenant y asignaciones por rol/contexto/vigencia.

### Modified Capabilities
- `rbac`: la resolución de permisos efectivos debe considerar asignaciones vigentes cuando el permiso depende de contexto académico; asignaciones vencidas no autorizan.
- `encrypted-fields-at-rest`: se aplica a PII real del modelo `Usuario`.

## Impact

- **Nuevos archivos**: `backend/app/models/usuarios.py`, `backend/app/repositories/usuarios.py`, `backend/app/services/usuarios.py`, `backend/app/api/v1/routers/usuarios.py`, `backend/app/schemas/usuarios.py`, `backend/alembic/versions/005_usuarios_asignaciones.py`.
- **Archivos modificados**: `backend/app/models/__init__.py`, `backend/app/repositories/__init__.py`, router registry, RBAC permission resolver, tests.
- **Dependencias**: C-06 archivado; requiere `AuthUser`, `Rol`, `Carrera`, `Cohorte`, `Materia`, cifrado AES-256 y `TenantScopedRepository` existentes.
- **Desbloquea**: C-08, C-09, C-13, C-14, C-16, C-18, C-19, C-20.
- **Governance**: CRITICO — implementación requiere aprobación explícita antes de tocar código.
