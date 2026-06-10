## Why

El backend tiene autenticación, RBAC y auditoría listos (C-01–C-05), pero no existe ninguna entidad del dominio académico. Sin `Carrera`, `Cohorte` y `Materia`, ningún módulo posterior puede existir: padrón, calificaciones, encuentros, equipos y comunicaciones dependen de estas tres entidades raíz. C-06 cierra el GATE 4 para el camino crítico y desbloquea el gran fork paralelo (C-07, C-15, C-17).

## What Changes

- Nuevos modelos SQLAlchemy: `Carrera`, `Cohorte`, `Materia` con `TenantScopedMixin` + soft delete
- Migración Alembic `004_estructura_academica`: tablas + constraints de unicidad + índices
- Endpoints ABM REST bajo `/api/admin/`:
  - `GET/POST /api/admin/carreras` · `GET/PATCH/DELETE /api/admin/carreras/{id}`
  - `GET/POST /api/admin/cohortes` · `GET/PATCH/DELETE /api/admin/cohortes/{id}`
  - `GET/POST /api/admin/materias` · `GET/PATCH/DELETE /api/admin/materias/{id}`
- Guard `require_permission("estructura:gestionar")` en todos los endpoints de ABM
- Seed del permiso `estructura:gestionar` en el rol ADMIN (delta sobre migración 003_rbac)
- Schemas Pydantic v2 (`extra='forbid'`) para request/response de cada entidad
- Suite de tests TDD: CRUD, unicidad por tenant, aislamiento multi-tenant, reglas de estado

**Nota sobre ADR-006**: `Materia` es el catálogo único del tenant (una sola definición por código). La entidad `Dictado` (instancia de Materia en carrera×cohorte) existe como concepto según ADR-006 y se implementará en changes posteriores cuando se necesite como contexto para calificaciones o equipos. Este change solo introduce el catálogo base.

**Nota sobre PA-01 y PA-07**: ADR-006 (`docs/ARQUITECTURA.md §10`) cierra PA-01 — catálogo único (`Materia`) + instancia futura (`Dictado`). PA-07 se resuelve con el modelo del KB: `Cohorte` tiene FK `carrera_id` (pertenece a una carrera); si en el futuro se necesitan cohortes transversales, es un change separado.

## Capabilities

### New Capabilities
- `estructura-academica`: ABM de `Carrera`, `Cohorte` y `Materia` con aislamiento tenant, unicidad por código, reglas de estado (activa/inactiva) y guard `estructura:gestionar`

### Modified Capabilities
<!-- No hay cambios en especificaciones existentes. El permiso `estructura:gestionar` es dato nuevo
     en la matriz RBAC, no un cambio en el comportamiento del motor de permisos (rbac spec). -->

## Impact

- **Nuevos archivos**: `backend/app/models/estructura.py`, `backend/app/repositories/estructura.py`, `backend/app/services/estructura.py`, `backend/app/api/v1/routers/estructura.py`, `backend/app/schemas/estructura.py`, `backend/alembic/versions/004_estructura_academica.py`
- **Archivo modificado**: migración 003 o fixture de seed RBAC para agregar `estructura:gestionar` al rol ADMIN
- **Dependencias**: requiere C-04 (RBAC guard disponible), C-02 (TenantScopedMixin + BaseRepository)
- **Desbloquea**: C-07 (usuarios y asignaciones), C-15 (avisos), C-17 (programas y fechas académicas), C-19 (panel de auditoría — junto con C-05 ya listo)
- **No hay cambios en contratos públicos existentes**: todos los endpoints de auth y RBAC quedan intactos
