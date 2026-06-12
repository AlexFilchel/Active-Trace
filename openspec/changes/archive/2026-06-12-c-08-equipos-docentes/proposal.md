## Why

Con usuarios y asignaciones implementados (C-07), el sistema puede registrar quién está asignado a qué, pero no ofrece las operaciones de alto nivel que el COORDINADOR necesita para gestionar equipos docentes a lo largo del ciclo académico: asignación masiva, clonado entre períodos, modificación en bloque de vigencias y exportación. Sin estas capacidades, cada inicio de cuatrimestre requiere reconfigurar manualmente cada asignación, lo que es inviable a escala.

## What Changes

- Vistas de **mis equipos** del docente autenticado (F4.2): materias y comisiones asignadas, rol, vigencia, estado.
- Endpoint de **gestión de asignaciones** (F4.3): listado filtrado de todas las asignaciones del tenant (COORDINADOR/ADMIN).
- **Asignación masiva** (F4.4): seleccionar N docentes y asignarlos en bloque a materia × carrera × cohorte × rol con vigencia, con autocompletado server-side para búsqueda (RN-30).
- **Clonar equipo** entre períodos (F4.5, RN-12): duplica asignaciones vigentes de un origen (materia × carrera × cohorte) a un destino con nuevas fechas.
- **Modificar vigencia general** del equipo (F4.6): actualiza `desde`/`hasta` de todas las asignaciones de un equipo en una sola operación.
- **Exportar equipo** a archivo descargable (F4.7): docente, rol, materia, carrera, cohorte, vigencia, estado.
- Registro de auditoría `ASIGNACION_MODIFICAR` en las operaciones que modifican asignaciones.

## Capabilities

### New Capabilities

- `equipos-docentes`: operaciones de gestión de equipo sobre el modelo `Asignacion` — mis-equipos, asignación masiva con autocompletado, clonado entre cohortes, modificación de vigencia en bloque y exportación.

### Modified Capabilities

- `usuarios-y-asignaciones`: no cambian los requerimientos del modelo ni del CRUD base; este change agrega operaciones de negocio de alto nivel encima de la misma tabla. Sin cambio de spec.

## Impact

- **Routers nuevos**: `app/routers/equipos.py` (`/api/equipos/*`)
- **Services nuevos**: `app/services/equipo_service.py` — lógica de clonado, masiva, vigencia en bloque, exportación
- **Repositories**: extensiones en `app/repositories/asignacion_repository.py` — queries de filtrado, búsqueda autocompletado, bulk-update de vigencias
- **Schemas nuevos**: `app/schemas/equipos.py` — requests/responses para las operaciones de equipo
- **Sin migración**: no se crean tablas nuevas; todo opera sobre `asignacion` (C-07)
- **Permisos requeridos**: `equipos:asignar` (COORDINADOR, ADMIN) — ya en la matriz C-04; `equipos:ver` para mis-equipos (todos los roles docentes)
- **Auditoría**: integra el helper de `AuditLog` (C-05) para `ASIGNACION_MODIFICAR`
