## ADDED Requirements

### Requirement: Docente puede ver sus equipos asignados
El sistema SHALL proveer al usuario autenticado una vista de todas sus asignaciones activas, incluyendo materia, carrera, cohorte, rol ejercido, vigencia y estado. Requiere permiso `equipos:ver`.

#### Scenario: Docente ve sus equipos
- **WHEN** un usuario con rol PROFESOR realiza `GET /api/equipos/mis-equipos`
- **THEN** el sistema devuelve únicamente las asignaciones del usuario autenticado dentro de su tenant, con materia, carrera, cohorte, rol, `desde`, `hasta` y `estado_vigencia`

#### Scenario: Docente sin asignaciones recibe lista vacía
- **WHEN** un usuario autenticado no tiene asignaciones
- **THEN** el sistema devuelve `[]` con status 200

#### Scenario: Tenant aislado
- **WHEN** dos usuarios de distintos tenants consultan sus equipos
- **THEN** cada uno ve únicamente las asignaciones de su propio tenant

---

### Requirement: Coordinador puede listar y filtrar todas las asignaciones del tenant
El sistema SHALL exponer un endpoint de gestión de asignaciones con filtros por materia, carrera, cohorte, rol, estado y nombre/id de docente. Requiere permiso `equipos:asignar`.

#### Scenario: Listado con filtro por materia
- **WHEN** un COORDINADOR realiza `GET /api/equipos/asignaciones?materia_id=<id>`
- **THEN** el sistema devuelve solo las asignaciones de esa materia dentro del tenant

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin permiso `equipos:asignar` accede al listado de asignaciones
- **THEN** el sistema responde 403

---

### Requirement: Asignación masiva de docentes a un equipo
El sistema SHALL permitir asignar múltiples docentes en bloque a una combinación materia × carrera × cohorte × rol con vigencia definida. Requiere permiso `equipos:asignar`.

#### Scenario: Asignación masiva exitosa
- **WHEN** un COORDINADOR envía `POST /api/equipos/asignaciones/masiva` con una lista de `usuario_id` y el contexto (materia, carrera, cohorte, rol, desde, hasta)
- **THEN** el sistema crea una `Asignacion` por cada usuario en el tenant activo y devuelve el conteo de asignaciones creadas

#### Scenario: Búsqueda de docentes con autocompletado
- **WHEN** se realiza `GET /api/equipos/docentes/buscar?q=<término>`
- **THEN** el sistema devuelve hasta 20 usuarios activos del tenant cuyo nombre o apellido contenga el término (case-insensitive)

#### Scenario: Docente ya asignado al mismo contexto
- **WHEN** se intenta asignar un docente que ya tiene una asignación vigente al mismo materia × carrera × cohorte × rol
- **THEN** el sistema rechaza con 409 Conflict indicando el usuario en conflicto

---

### Requirement: Clonado de equipo entre períodos
El sistema SHALL clonar todas las asignaciones vigentes de un equipo origen (materia × carrera × cohorte) a un destino, con nuevas fechas de vigencia. La operación es atómica. Requiere permiso `equipos:asignar`.

#### Scenario: Clonado exitoso
- **WHEN** un COORDINADOR envía `POST /api/equipos/clonar` con origen (materia_id, carrera_id, cohorte_id) y destino (cohorte_id destino, desde, hasta)
- **THEN** el sistema duplica todas las asignaciones vigentes del origen en el destino dentro de la misma transacción y devuelve el número de asignaciones clonadas

#### Scenario: Rollback si falla alguna inserción
- **WHEN** una de las inserciones del clonado falla (p.ej. constraint de unicidad)
- **THEN** el sistema revierte toda la operación y no crea ninguna asignación parcial

#### Scenario: Origen sin asignaciones vigentes
- **WHEN** el equipo origen no tiene asignaciones con `estado_vigencia = activa`
- **THEN** el sistema devuelve 422 con mensaje descriptivo

---

### Requirement: Modificación de vigencia general del equipo
El sistema SHALL actualizar las fechas `desde`/`hasta` de todas las asignaciones de un equipo (materia × carrera × cohorte) en una sola operación. Requiere permiso `equipos:asignar`.

#### Scenario: Vigencia actualizada en bloque
- **WHEN** un COORDINADOR realiza `PATCH /api/equipos/vigencia` con (materia_id, carrera_id, cohorte_id, desde, hasta)
- **THEN** el sistema actualiza `desde` y `hasta` en todas las asignaciones del equipo dentro del tenant y registra `ASIGNACION_MODIFICAR` con `filas_afectadas`

#### Scenario: Equipo inexistente
- **WHEN** no existe ninguna asignación para la combinación materia × carrera × cohorte en el tenant
- **THEN** el sistema devuelve 404

---

### Requirement: Exportación del equipo docente
El sistema SHALL generar un archivo descargable con el detalle de todas las asignaciones del equipo. Requiere permiso `equipos:asignar`.

#### Scenario: Exportación exitosa
- **WHEN** un COORDINADOR realiza `GET /api/equipos/exportar?materia_id=<id>&carrera_id=<id>&cohorte_id=<id>`
- **THEN** el sistema devuelve un archivo CSV/XLSX con columnas: docente, rol, materia, carrera, cohorte, vigencia (desde/hasta), estado

#### Scenario: Sin asignaciones para exportar
- **WHEN** no hay asignaciones para el filtro solicitado
- **THEN** el sistema devuelve un archivo vacío (solo headers) con status 200

---

### Requirement: Auditoría de operaciones de equipo
El sistema SHALL registrar una entrada en `AuditLog` con código `ASIGNACION_MODIFICAR` para toda operación que cree o modifique asignaciones en bloque (masiva, clonado, vigencia en bloque).

#### Scenario: Clonado registra auditoría
- **WHEN** se completa un clonado de equipo
- **THEN** existe un `AuditLog` con `accion = ASIGNACION_MODIFICAR`, el `actor` del request, y `filas_afectadas` igual al número de asignaciones clonadas

#### Scenario: Asignación masiva registra auditoría
- **WHEN** se completa una asignación masiva
- **THEN** existe un `AuditLog` con `accion = ASIGNACION_MODIFICAR` y `filas_afectadas` igual al número de asignaciones creadas
