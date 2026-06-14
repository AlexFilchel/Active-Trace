# Proposal: C-17 — Programas y Fechas Académicas

## Why

La coordinación académica necesita un lugar centralizado para publicar los programas oficiales de cada materia y las fechas de evaluaciones (parciales, TPs, coloquios), que hoy se gestionan por WhatsApp o en documentos externos. Sin este módulo, no hay fuente de verdad accesible para docentes y coordinación, y la generación de contenido para el aula virtual (LMS) es manual y propensa a errores.

## What Changes

- Modelo `ProgramaMateria`: documento oficial de una materia para una combinación materia × carrera × cohorte, con referencia de archivo opaca (URL/path al servicio de almacenamiento).
- Modelo `FechaAcademica`: fecha de instancia evaluativa (parcial, TP, coloquio, recuperatorio) por materia × cohorte × número de instancia y período.
- API `/api/programas` (CRUD + asociar): registrar y listar programas por materia/carrera/cohorte. Permiso `estructura:gestionar`.
- API `/api/fechas-academicas` (CRUD): registrar, editar y listar fechas evaluativas. Permiso `estructura:gestionar`. Filtro por materia, cohorte, tipo y período.
- Migración `014_programas_fechas_academicas`: tablas `programa_materia` y `fecha_academica`.
- Auditoría: `PROGRAMA_CREAR`, `FECHA_ACAT_CREAR`, `FECHA_ACAT_EDITAR`.
- Generación de fragmento LMS: endpoint que devuelve texto formateado con las fechas de evaluación de una materia/cohorte, listo para publicar en el aula virtual.

## Capabilities

### New Capabilities

- `programas-y-fechas-academicas`: Gestión de programas de materia (documento por materia×carrera×cohorte) y fechas académicas (parciales, TPs, coloquios) con listado tabular y generación de fragmento LMS.

### Modified Capabilities

*(ninguna — módulo nuevo)*

## Impact

- **Nueva migración**: `014_programas_fechas_academicas` (down_revision `013_tareas_internas`).
- **Nuevos modelos**: `ProgramaMateria`, `FechaAcademica` (ambos con `TenantScopedMixin`).
- **Nuevos endpoints**: 7 rutas bajo `/api/programas` y `/api/fechas-academicas`.
- **Permiso reutilizado**: `estructura:gestionar` (ya existe en C-06, asignado a COORDINADOR y ADMIN).
- **Dependencia**: `C-06 estructura-academica` (FK a `materia`, `carrera`, `cohorte`).
- **Governance**: BAJO — no toca auth, RBAC ni PII. Operación CRUD pura.
