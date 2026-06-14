# Spec: tareas-internas

## ADDED Requirements

### Requirement: Crear tarea
El sistema SHALL permitir a COORDINADOR y PROFESOR crear tareas asignadas a un usuario del mismo tenant, con descripción, materia opcional y referencia de contexto opcional. El estado inicial es siempre `Pendiente`. Se registra `asignado_por` como el actor que crea.

#### Scenario: Crear tarea válida
- **WHEN** un COORDINADOR envía `POST /api/tareas` con `asignado_a`, `descripcion` y `materia_id` opcional
- **THEN** el sistema crea la tarea en estado `Pendiente`, retorna 201 con todos los campos incluyendo `asignado_por` = actor actual

#### Scenario: Sin permiso tareas:gestionar
- **WHEN** un usuario sin permiso `tareas:gestionar` intenta crear una tarea
- **THEN** el sistema retorna 403

#### Scenario: Descripción vacía
- **WHEN** se envía `descripcion` con cadena vacía o campo ausente
- **THEN** el sistema retorna 422

#### Scenario: Campo extra en body
- **WHEN** el body incluye un campo no declarado en el schema
- **THEN** el sistema retorna 422 (`extra_forbidden`)

---

### Requirement: Cambiar estado de tarea
El sistema SHALL permitir cambiar el estado de una tarea según la máquina de estados: `Pendiente → En progreso → Resuelta | Cancelada`. El usuario asignado puede mover la tarea a `En progreso` o `Resuelta`. El asignador (o COORDINADOR/ADMIN) puede cancelar. Transiciones inválidas SHALL ser rechazadas con 422.

#### Scenario: Avanzar estado válido
- **WHEN** el usuario asignado envía `PATCH /api/tareas/{id}` con `estado: "En progreso"`
- **THEN** el sistema actualiza el estado y registra auditoría `TAREA_ESTADO`

#### Scenario: Transición inválida
- **WHEN** se intenta mover una tarea en estado `Resuelta` a `En progreso`
- **THEN** el sistema retorna 422 con mensaje descriptivo

#### Scenario: Cancelar por asignador
- **WHEN** el `asignado_por` (o un COORDINADOR) envía `estado: "Cancelada"`
- **THEN** el sistema acepta la transición y retorna 200

#### Scenario: Tarea de otro tenant
- **WHEN** se intenta modificar una tarea de otro tenant usando un id válido pero ajeno
- **THEN** el sistema retorna 404

---

### Requirement: Mis tareas (vista personal)
El sistema SHALL exponer `GET /api/tareas/mis-tareas` que retorna las tareas donde el actor es `asignado_a` O `asignado_por`, filtradas opcionalmente por `estado` y `materia_id`. El listado NO incluye tareas de otros usuarios.

#### Scenario: Listar tareas asignadas al actor
- **WHEN** un PROFESOR autenticado llama `GET /api/tareas/mis-tareas`
- **THEN** el sistema retorna solo las tareas donde ese profesor es `asignado_a` o `asignado_por`

#### Scenario: Filtrar por estado
- **WHEN** se pasa query param `estado=Pendiente`
- **THEN** el sistema retorna solo tareas con ese estado

#### Scenario: Filtrar por materia
- **WHEN** se pasa query param `materia_id=<uuid>`
- **THEN** el sistema retorna solo tareas de esa materia (incluye las sin materia si no se filtra)

---

### Requirement: Administración global de tareas
El sistema SHALL exponer `GET /api/tareas` (modo admin) accesible a COORDINADOR y ADMIN, que retorna todas las tareas del tenant con filtros opcionales por `asignado_a`, `asignado_por`, `materia_id`, `estado` y búsqueda en `descripcion`.

#### Scenario: Listar todas las tareas del tenant
- **WHEN** un COORDINADOR llama `GET /api/tareas`
- **THEN** el sistema retorna todas las tareas del tenant (no solo las propias)

#### Scenario: Filtros combinados
- **WHEN** se pasan `asignado_a=<uuid>` y `estado=Pendiente`
- **THEN** el sistema aplica ambos filtros en AND

#### Scenario: Aislamiento de tenant
- **WHEN** un COORDINADOR del tenant A consulta `GET /api/tareas`
- **THEN** el sistema NO retorna tareas de otro tenant

---

### Requirement: Comentarios en hilo
El sistema SHALL permitir agregar comentarios a una tarea mediante `POST /api/tareas/{id}/comentarios`. Cualquier usuario con permiso `tareas:gestionar` puede comentar. El comentario registra `autor_id` desde el JWT. No se pueden editar ni borrar comentarios (append-only). Se lista con `GET /api/tareas/{id}/comentarios`.

#### Scenario: Agregar comentario
- **WHEN** un PROFESOR envía `POST /api/tareas/{id}/comentarios` con `texto` no vacío
- **THEN** el sistema crea el comentario, retorna 201, registra auditoría `TAREA_COMENTAR`

#### Scenario: Listar comentarios
- **WHEN** se llama `GET /api/tareas/{id}/comentarios`
- **THEN** el sistema retorna todos los comentarios de la tarea en orden cronológico ascendente

#### Scenario: Texto vacío rechazado
- **WHEN** se envía `texto` con cadena vacía
- **THEN** el sistema retorna 422

#### Scenario: Comentario en tarea de otro tenant
- **WHEN** se intenta comentar una tarea de otro tenant
- **THEN** el sistema retorna 404

---

### Requirement: Auditoría de tareas
El sistema SHALL registrar entradas de `AuditLog` para las acciones `TAREA_CREAR`, `TAREA_ESTADO` y `TAREA_COMENTAR` incluyendo `tarea_id` en el campo `detalle`.

#### Scenario: Audit al crear
- **WHEN** se crea una tarea exitosamente
- **THEN** existe un `AuditLog` con `accion=TAREA_CREAR`, `actor_id` del creador y `tarea_id` en detalle

#### Scenario: Audit al cambiar estado
- **WHEN** se cambia el estado de una tarea
- **THEN** existe un `AuditLog` con `accion=TAREA_ESTADO`, estado anterior y nuevo en detalle
