## ADDED Requirements

### Requirement: Crear encuentro recurrente genera todas las instancias
El sistema SHALL permitir crear un `SlotEncuentro` recurrente que genere automáticamente una `InstanciaEncuentro` en estado `Programado` por cada semana, desde `fecha_inicio` y durante `cant_semanas` semanas. La operación es atómica. Requiere permiso `encuentros:gestionar`.

#### Scenario: Recurrencia de N semanas genera N instancias
- **WHEN** un PROFESOR envía `POST /api/encuentros/recurrente` con `materia_id`, `dia_semana`, `hora`, `fecha_inicio`, `cant_semanas = 8`, `titulo` y `meet_url`
- **THEN** el sistema crea un `SlotEncuentro` y exactamente 8 `InstanciaEncuentro` en estado `Programado`, con fechas `fecha_inicio + 7*k` para `k` en `0..7`, dentro del tenant del usuario autenticado

#### Scenario: fecha_inicio incoherente con dia_semana es rechazada
- **WHEN** se envía `fecha_inicio` cuyo día de la semana no coincide con `dia_semana`
- **THEN** el sistema responde 422 sin crear el slot ni instancias

#### Scenario: cant_semanas fuera de rango es rechazada
- **WHEN** se envía `cant_semanas` mayor al máximo permitido o menor a 1 para un recurrente
- **THEN** el sistema responde 422

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin permiso `encuentros:gestionar` intenta crear un encuentro
- **THEN** el sistema responde 403 y no crea ningún registro

---

### Requirement: Crear encuentro único
El sistema SHALL permitir crear un encuentro puntual sin recurrencia, materializado como un `SlotEncuentro` con `cant_semanas = 0` y una única `InstanciaEncuentro` en la fecha indicada. Requiere permiso `encuentros:gestionar`.

#### Scenario: Encuentro único crea una sola instancia
- **WHEN** un PROFESOR envía `POST /api/encuentros/unico` con `materia_id`, `fecha`, `hora`, `titulo` y `meet_url`
- **THEN** el sistema crea un `SlotEncuentro` con `cant_semanas = 0` y exactamente una `InstanciaEncuentro` en `Programado` para esa fecha y hora

---

### Requirement: Editar instancia de encuentro
El sistema SHALL permitir modificar de una `InstanciaEncuentro` únicamente los campos `estado`, `meet_url`, `video_url` y `comentario`. Requiere permiso `encuentros:gestionar`.

#### Scenario: Marcar realizado con grabación
- **WHEN** un PROFESOR envía `PATCH /api/encuentros/instancias/{id}` con `estado = Realizado` y `video_url`
- **THEN** la instancia queda en estado `Realizado` con el `video_url` guardado

#### Scenario: Cancelar instancia
- **WHEN** se envía `PATCH /api/encuentros/instancias/{id}` con `estado = Cancelado`
- **THEN** la instancia queda en estado `Cancelado`

#### Scenario: Campo no permitido es rechazado
- **WHEN** el payload incluye un campo fuera de `{estado, meet_url, video_url, comentario}` (p.ej. `fecha`)
- **THEN** el sistema responde 422 (schema `extra='forbid'`)

#### Scenario: Instancia inexistente
- **WHEN** se edita una instancia con id inexistente en el tenant
- **THEN** el sistema responde 404

---

### Requirement: Generar bloque HTML para el aula virtual
El sistema SHALL generar un fragmento HTML con el calendario de encuentros de una materia y sus grabaciones, listo para copiar al LMS. Requiere permiso `encuentros:gestionar`.

#### Scenario: Bloque con encuentros y grabaciones
- **WHEN** un PROFESOR realiza `GET /api/encuentros/bloque-html?materia_id=<id>`
- **THEN** el sistema devuelve un HTML con las instancias ordenadas por fecha, incluyendo título, fecha, hora, enlace `meet_url` y, cuando exista, enlace `video_url`, con el contenido escapado de forma segura

#### Scenario: Materia sin encuentros
- **WHEN** la materia no tiene instancias de encuentro
- **THEN** el sistema devuelve un bloque HTML vacío (sin filas) con status 200

---

### Requirement: Vista de administración de encuentros del tenant
El sistema SHALL exponer un listado transversal de todas las instancias de encuentro del tenant, independientemente del docente que las creó, con filtros opcionales por materia, cohorte, estado y rango de fechas. Requiere permiso `encuentros:gestionar`.

#### Scenario: Coordinación ve todos los encuentros del tenant
- **WHEN** un COORDINADOR realiza `GET /api/encuentros`
- **THEN** el sistema devuelve todas las instancias del tenant, no solo las propias

#### Scenario: Tenant aislado
- **WHEN** dos usuarios de distintos tenants listan encuentros
- **THEN** cada uno ve únicamente las instancias de su propio tenant

#### Scenario: Filtro por estado
- **WHEN** se realiza `GET /api/encuentros?estado=Realizado`
- **THEN** el sistema devuelve solo las instancias en estado `Realizado`

---

### Requirement: Registro de guardia por el tutor
El sistema SHALL permitir registrar una `Guardia` asociada a una asignación del usuario autenticado, con materia, carrera, cohorte, día, horario, estado y comentarios. Requiere permiso `guardias:registrar`.

#### Scenario: Tutor registra una guardia
- **WHEN** un TUTOR envía `POST /api/guardias` con `asignacion_id`, `materia_id`, `carrera_id`, `cohorte_id`, `dia`, `horario` y `comentarios`
- **THEN** el sistema crea la `Guardia` en estado `Pendiente` dentro del tenant del usuario autenticado

#### Scenario: Asignación de otro tenant es rechazada
- **WHEN** se envía un `asignacion_id` que no pertenece al tenant del usuario autenticado
- **THEN** el sistema responde 404 y no crea la guardia

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin permiso `guardias:registrar` intenta registrar una guardia
- **THEN** el sistema responde 403

---

### Requirement: Consulta y exportación global de guardias
El sistema SHALL permitir consultar el registro de guardias del tenant con filtros (materia, carrera, cohorte, estado) y exportarlo a CSV. Requiere permiso `guardias:registrar`.

#### Scenario: Consulta filtrada por materia
- **WHEN** un COORDINADOR realiza `GET /api/guardias?materia_id=<id>`
- **THEN** el sistema devuelve solo las guardias de esa materia dentro del tenant

#### Scenario: Exportación a CSV
- **WHEN** un COORDINADOR realiza `GET /api/guardias/exportar`
- **THEN** el sistema devuelve un archivo CSV con columnas: usuario_id, materia, carrera, cohorte, dia, horario, estado, comentarios

#### Scenario: Sin guardias para exportar
- **WHEN** no hay guardias para el filtro solicitado
- **THEN** el sistema devuelve un CSV con solo los headers y status 200

---

### Requirement: Auditoría de operaciones de encuentros y guardias
El sistema SHALL registrar una entrada en `AuditLog` para las operaciones que crean o modifican encuentros y guardias.

#### Scenario: Crear encuentro recurrente registra auditoría
- **WHEN** se completa la creación de un encuentro recurrente
- **THEN** existe un `AuditLog` con `accion = ENCUENTRO_GESTIONAR`, el `actor` del request y `filas_afectadas` igual al número de instancias generadas

#### Scenario: Registrar guardia registra auditoría
- **WHEN** se completa el registro de una guardia
- **THEN** existe un `AuditLog` con `accion = GUARDIA_REGISTRAR` y el `actor` del request
