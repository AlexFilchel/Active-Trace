## ADDED Requirements

### Requirement: Ver acciones por día
El sistema SHALL exponer `GET /api/auditoria/acciones-por-dia` que retorna el conteo de acciones del tenant agrupado por fecha. COORDINADOR solo ve sus propias acciones. Acepta filtros opcionales `desde`, `hasta`, `materia_id`, `usuario_id`.

#### Scenario: ADMIN ve todas las acciones del tenant
- **WHEN** un ADMIN llama `GET /api/auditoria/acciones-por-dia`
- **THEN** el sistema retorna una lista de `{ fecha, total }` ordenada por fecha ASC con conteos de TODOS los usuarios del tenant

#### Scenario: COORDINADOR solo ve sus propias acciones
- **WHEN** un COORDINADOR llama `GET /api/auditoria/acciones-por-dia`
- **THEN** el sistema retorna solo las acciones cuyo `actor_id` coincide con el usuario autenticado

#### Scenario: Filtro por rango de fechas
- **WHEN** se pasan `desde=YYYY-MM-DD` y `hasta=YYYY-MM-DD`
- **THEN** el sistema retorna solo acciones dentro del rango (inclusive)

#### Scenario: Sin permiso auditoria:ver → 403
- **WHEN** un usuario sin permiso `auditoria:ver` llama cualquier endpoint de `/api/auditoria/`
- **THEN** el sistema retorna 403

---

### Requirement: Ver estado de comunicaciones por docente
El sistema SHALL exponer `GET /api/auditoria/estado-comunicaciones` que retorna el conteo de acciones de tipo comunicación agrupado por docente (actor_id) y estado inferido. COORDINADOR solo ve sus propias acciones.

#### Scenario: Resumen de comunicaciones del tenant
- **WHEN** un ADMIN llama `GET /api/auditoria/estado-comunicaciones`
- **THEN** el sistema retorna una lista de `{ actor_id, accion, total }` para acciones con prefijo `COMUNICACION_`

#### Scenario: Aislamiento de scope para COORDINADOR
- **WHEN** un COORDINADOR llama `GET /api/auditoria/estado-comunicaciones`
- **THEN** el sistema solo retorna entradas donde `actor_id` es el propio COORDINADOR

---

### Requirement: Ver interacciones por docente y materia
El sistema SHALL exponer `GET /api/auditoria/interacciones-docente` que retorna el conteo de acciones agrupado por `actor_id` y materia extraída del `detalle`. COORDINADOR solo ve sus propias acciones. Acepta filtros opcionales `desde`, `hasta`, `materia_id`, `usuario_id`.

#### Scenario: Métricas de interacción del tenant
- **WHEN** un ADMIN llama `GET /api/auditoria/interacciones-docente`
- **THEN** el sistema retorna una lista de `{ actor_id, accion, total }` ordenada por `total` DESC

#### Scenario: Filtro por usuario específico
- **WHEN** se pasa `usuario_id=<uuid>`
- **THEN** el sistema retorna solo las entradas del actor indicado (si es ADMIN o si el usuario_id coincide con el COORDINADOR)

---

### Requirement: Log paginado de últimas acciones
El sistema SHALL exponer `GET /api/auditoria/log` que retorna los últimos N registros de AuditLog del tenant ordenados por `created_at` DESC. COORDINADOR solo ve sus propias acciones. Acepta filtros `desde`, `hasta`, `materia_id`, `usuario_id`, `accion`. El límite máximo es 500; el default es 200 (RN-F9.1).

#### Scenario: Log con límite default
- **WHEN** un ADMIN llama `GET /api/auditoria/log` sin parámetros
- **THEN** el sistema retorna hasta 200 registros ordenados por `created_at` DESC

#### Scenario: Límite configurable
- **WHEN** se pasa `limit=50`
- **THEN** el sistema retorna hasta 50 registros

#### Scenario: Límite mayor a 500 → rechazado
- **WHEN** se pasa `limit=501`
- **THEN** el sistema retorna 422

#### Scenario: Filtro por acción
- **WHEN** se pasa `accion=TAREA_CREAR`
- **THEN** el sistema retorna solo entradas con `accion=TAREA_CREAR`

#### Scenario: Scope propio para COORDINADOR
- **WHEN** un COORDINADOR llama `GET /api/auditoria/log`
- **THEN** el sistema retorna solo sus propias entradas, aunque el tenant tenga más

---

### Requirement: Permiso auditoria:ver
El sistema SHALL incluir el permiso `auditoria:ver` y asignarlo a los roles ADMIN, COORDINADOR y FINANZAS del tenant en la migración `015`.

#### Scenario: Seed de permiso en migración
- **WHEN** se ejecuta la migración `015_auditoria_permiso`
- **THEN** existe un permiso `auditoria:ver` en cada tenant y está asignado a ADMIN, COORDINADOR y FINANZAS

#### Scenario: Idempotente con ON CONFLICT DO NOTHING
- **WHEN** la migración se ejecuta dos veces
- **THEN** no produce errores ni duplicados
