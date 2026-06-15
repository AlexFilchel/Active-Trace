## ADDED Requirements

### Requirement: Modelos HiloMensaje y MensajeInterno con aislamiento tenant

El sistema SHALL mantener las tablas `hilo_mensaje` y `mensaje_interno` con `tenant_id` en cada tabla. `HiloMensaje` SHALL tener `id`, `tenant_id`, `asunto`, `creado_por` (FK → `usuario.id`), `created_at`, `deleted_at`. `MensajeInterno` SHALL tener `id`, `tenant_id`, `hilo_id` (FK → `hilo_mensaje.id`), `remitente_id` (FK → `usuario.id`), `destinatario_id` (FK → `usuario.id`), `cuerpo`, `leido` (boolean, default false), `sent_at`, `deleted_at`. Los repositorios SHALL filtrar por `tenant_id` en todas las queries.

#### Scenario: Mensajes de distintos tenants no se mezclan

- **WHEN** dos tenants crean hilos con el mismo asunto
- **THEN** cada tenant solo ve sus propios hilos al consultar `/api/inbox/hilos`
- **AND** no es posible leer mensajes del otro tenant

---

### Requirement: Iniciar un hilo de mensajería interna

El sistema SHALL exponer `POST /api/inbox/hilos` que crea un `HiloMensaje` y el primer `MensajeInterno` en una sola operación. El `remitente_id` SHALL resolverse desde el JWT (no del body). El `destinatario_id` SHALL ser un `usuario.id` activo del mismo tenant. Si el destinatario no existe o pertenece a otro tenant, el sistema SHALL responder HTTP 404. El sistema SHALL retornar HTTP 201 con el hilo creado y el primer mensaje.

#### Scenario: Crear hilo con destinatario del mismo tenant

- **WHEN** usuario A hace `POST /api/inbox/hilos` con `destinatario_id` del usuario B del mismo tenant
- **THEN** el sistema responde HTTP 201
- **AND** se crea un `HiloMensaje` y un `MensajeInterno` con `remitente_id` = A, `destinatario_id` = B

#### Scenario: Destinatario de otro tenant es rechazado

- **WHEN** el `destinatario_id` no existe en el tenant del remitente
- **THEN** el sistema responde HTTP 404

#### Scenario: Remitente no puede enviarse mensajes a sí mismo

- **WHEN** `destinatario_id` es el mismo `usuario.id` que el remitente
- **THEN** el sistema responde HTTP 422

---

### Requirement: Listar hilos del inbox propio

El sistema SHALL exponer `GET /api/inbox/hilos` que retorna los hilos donde el usuario autenticado tiene al menos un `MensajeInterno` como destinatario. Solo SHALL retornar hilos no eliminados (`deleted_at IS NULL`). La respuesta SHALL incluir el último mensaje del hilo y el conteo de mensajes no leídos. No SHALL incluir hilos de otros usuarios.

#### Scenario: Inbox muestra solo hilos del usuario autenticado

- **WHEN** usuario A consulta `GET /api/inbox/hilos`
- **THEN** solo aparecen hilos donde A es destinatario de al menos un mensaje
- **AND** no aparecen hilos de usuario B aunque estén en el mismo tenant

#### Scenario: Hilo con mensajes no leídos aparece marcado

- **WHEN** usuario A recibe un mensaje en un hilo que aún no leyó
- **THEN** ese hilo aparece con `mensajes_no_leidos > 0`

---

### Requirement: Leer mensajes de un hilo

El sistema SHALL exponer `GET /api/inbox/hilos/{hilo_id}/mensajes` que retorna todos los `MensajeInterno` del hilo, ordenados por `sent_at` ascendente. Solo usuarios que participan en el hilo (como remitente o destinatario en cualquier mensaje) SHALL poder leer el hilo. Un usuario sin participación SHALL recibir HTTP 403.

#### Scenario: Participante lee los mensajes del hilo

- **WHEN** usuario A (destinatario del primer mensaje) consulta `GET /api/inbox/hilos/{id}/mensajes`
- **THEN** el sistema responde HTTP 200 con todos los mensajes del hilo ordenados por sent_at

#### Scenario: No participante recibe 403

- **WHEN** usuario C (sin ningún mensaje en el hilo) consulta los mensajes del hilo
- **THEN** el sistema responde HTTP 403

---

### Requirement: Responder dentro de un hilo y marcar como leído

El sistema SHALL exponer `POST /api/inbox/hilos/{hilo_id}/mensajes` que agrega un `MensajeInterno` al hilo existente. El `remitente_id` SHALL resolverse desde el JWT. El `destinatario_id` SHALL estar en el body. Al leer los mensajes de un hilo (`GET /api/inbox/hilos/{hilo_id}/mensajes`), el sistema SHALL marcar como `leido=true` todos los `MensajeInterno` donde `destinatario_id` = usuario autenticado.

#### Scenario: Respuesta se agrega al hilo existente

- **WHEN** usuario B responde con `POST /api/inbox/hilos/{id}/mensajes`
- **THEN** el sistema responde HTTP 201
- **AND** el nuevo mensaje aparece en `GET /api/inbox/hilos/{id}/mensajes` con `remitente_id` = B

#### Scenario: Leer mensajes marca como leído

- **WHEN** usuario A hace `GET /api/inbox/hilos/{id}/mensajes`
- **THEN** todos los mensajes del hilo donde `destinatario_id` = A quedan con `leido = true`
- **AND** el conteo `mensajes_no_leidos` del hilo baja a 0 en el siguiente `GET /api/inbox/hilos`
