## Purpose
Definir el registro append-only de auditoría, sus garantías de inmutabilidad, atribución de actor e aislamiento multi-tenant para acciones sensibles del sistema.
## Requirements
### Requirement: Registro inmutable de acciones significativas
El sistema SHALL mantener una tabla `audit_log` que registra acciones significativas con los campos: `id` (UUID), `tenant_id`, `fecha_hora`, `actor_id` (FK → Usuario), `impersonado_id` (FK → Usuario, nullable), `materia_id` (FK → Materia, nullable), `accion` (código textual estandarizado), `detalle` (JSON, nullable), `filas_afectadas` (entero), `ip` (texto, nullable), `user_agent` (texto, nullable). Los registros de `audit_log` NO tienen `updated_at` ni `deleted_at`.

#### Scenario: Registro de auditoría es creado correctamente
- **WHEN** se llama a `audit_action` con actor, tenant, código de acción y detalle
- **THEN** se persiste un registro en `audit_log` con todos los campos especificados

#### Scenario: Registro sin materia es válido
- **WHEN** se registra una acción de auditoría sin `materia_id`
- **THEN** el registro se persiste con `materia_id = NULL`

---

### Requirement: Enforcement append-only a nivel aplicación
El sistema SHALL garantizar que ningún código de aplicación pueda actualizar o eliminar registros de `audit_log`. El repositorio `AuditLogRepository` SHALL exponer únicamente operaciones de creación y lectura.

#### Scenario: Intento de update desde código de aplicación falla en compilación/runtime
- **WHEN** se intenta llamar a un método de update sobre `AuditLogRepository`
- **THEN** el método no existe y el intento falla antes de llegar a la DB

#### Scenario: Intento de delete desde código de aplicación falla en compilación/runtime
- **WHEN** se intenta llamar a un método de delete (soft o físico) sobre `AuditLogRepository`
- **THEN** el método no existe y el intento falla antes de llegar a la DB

---

### Requirement: Enforcement append-only a nivel base de datos
La migración `004_audit_log` SHALL crear un trigger PostgreSQL `audit_log_immutable` que rechace cualquier operación UPDATE o DELETE sobre la tabla `audit_log` con una excepción de base de datos.

#### Scenario: UPDATE directo en DB es rechazado
- **WHEN** se ejecuta `UPDATE audit_log SET accion = 'X' WHERE id = :id` directamente en la DB
- **THEN** la base de datos lanza una excepción y rechaza la operación

#### Scenario: DELETE directo en DB es rechazado
- **WHEN** se ejecuta `DELETE FROM audit_log WHERE id = :id` directamente en la DB
- **THEN** la base de datos lanza una excepción y rechaza la operación

---

### Requirement: Helper de auditoría con códigos estandarizados
El sistema SHALL proporcionar una función `audit_action` callable desde cualquier service o router para registrar acciones con un código estandarizado. La función SHALL aceptar: `session`, `actor_id`, `tenant_id`, `accion` (código), y opcionalmente `detalle` (dict), `materia_id`, `filas_afectadas`, `ip`, `user_agent`, `impersonando_id`.

#### Scenario: Acción con código estandarizado es registrada
- **WHEN** un service llama a `audit_action(session=..., actor_id=..., tenant_id=..., accion="CALIFICACIONES_IMPORTAR", filas_afectadas=42)`
- **THEN** se crea un registro en `audit_log` con el código `CALIFICACIONES_IMPORTAR` y `filas_afectadas=42`

#### Scenario: Acción con detalle JSON es registrada
- **WHEN** se llama a `audit_action(..., detalle={"materia": "PROG_I", "version": "v3"})`
- **THEN** el campo `detalle` del registro contiene el JSON especificado

---

### Requirement: Impersonación requiere permiso explícito
El sistema SHALL requerir el permiso `impersonacion:usar` para iniciar una sesión de impersonación. Sin este permiso, `POST /api/auth/impersonate/{user_id}` SHALL retornar HTTP 403.

#### Scenario: Usuario sin permiso de impersonación recibe 403
- **WHEN** un usuario sin el permiso `impersonacion:usar` llama a `POST /api/auth/impersonate/{target_id}`
- **THEN** el sistema retorna HTTP 403

#### Scenario: Usuario con permiso puede iniciar impersonación
- **WHEN** un usuario con `impersonacion:usar` llama a `POST /api/auth/impersonate/{target_id}`
- **THEN** el sistema retorna un nuevo access token con el claim `impersonating_user_id = target_id`

---

### Requirement: Sesión de impersonación es distinguible
El sistema SHALL emitir un access token con el claim adicional `impersonating_user_id` cuando una sesión es de impersonación. El claim `user_id` del token SHALL ser siempre el usuario que impersona (actor real), nunca el impersonado.

#### Scenario: Token de impersonación contiene claim distinguible
- **WHEN** se inicia una sesión de impersonación
- **THEN** el access token contiene `user_id = actor_real` y `impersonating_user_id = usuario_impersonado`

#### Scenario: Token normal no contiene claim de impersonación
- **WHEN** un usuario inicia sesión normalmente
- **THEN** el access token NO contiene el claim `impersonating_user_id`

---

### Requirement: Acciones bajo impersonación se atribuyen al actor real
El sistema SHALL garantizar que toda acción registrada en `audit_log` durante una sesión de impersonación tenga `actor_id = usuario_que_impersona` e `impersonado_id = usuario_impersonado`. El usuario impersonado NO aparece como actor de ninguna acción que no haya realizado él mismo.

#### Scenario: Audit log registra actor real bajo impersonación
- **WHEN** el usuario A (actor real) impersona al usuario B y realiza una acción
- **THEN** el registro en `audit_log` tiene `actor_id = A.id` e `impersonado_id = B.id`

#### Scenario: Usuario B no aparece como actor de acciones de A bajo impersonación
- **WHEN** el usuario A impersona a B y ejecuta la acción `CALIFICACIONES_IMPORTAR`
- **THEN** en `audit_log` el campo `actor_id` es A, no B

---

### Requirement: Inicio y fin de impersonación son auditados
El sistema SHALL registrar en `audit_log` los eventos `IMPERSONACION_INICIAR` y `IMPERSONACION_FINALIZAR` con el actor real y el usuario impersonado.

#### Scenario: IMPERSONACION_INICIAR es registrado
- **WHEN** el usuario A inicia una sesión de impersonación sobre el usuario B
- **THEN** se crea un registro en `audit_log` con `accion = "IMPERSONACION_INICIAR"`, `actor_id = A.id`, `impersonado_id = B.id`

#### Scenario: IMPERSONACION_FINALIZAR es registrado
- **WHEN** el usuario A finaliza la sesión de impersonación sobre el usuario B (vía `POST /api/auth/impersonate/end`)
- **THEN** se crea un registro en `audit_log` con `accion = "IMPERSONACION_FINALIZAR"`, `actor_id = A.id`, `impersonado_id = B.id`

---

### Requirement: Aislamiento multi-tenant del log de auditoría
El sistema SHALL garantizar que los registros de `audit_log` de un tenant nunca sean accesibles desde otro tenant. Todo query sobre `audit_log` SHALL filtrar por `tenant_id`.

#### Scenario: Registros de tenant A no visibles desde tenant B
- **WHEN** se consultan registros de `audit_log` para el tenant B
- **THEN** los registros del tenant A no aparecen en el resultado

### Requirement: Eventos de auditoría de comunicaciones
El sistema SHALL registrar eventos estandarizados para acciones significativas del módulo de comunicaciones.

- `COMUNICACION_ENVIAR` MUST registrarse al confirmar enqueue de comunicaciones.
- `COMUNICACION_APROBAR` MUST registrarse al aprobar un lote o comunicación individual.
- `COMUNICACION_CANCELAR` MUST registrarse al cancelar un lote o comunicación individual.
- Los detalles de auditoría MUST incluir identificadores internos (`lote_id`, `comunicacion_id`, `materia_id`) y `filas_afectadas`, pero MUST NOT incluir destinatarios en plaintext.

#### Scenario: Enviar comunicación queda auditado
- **WHEN** un usuario confirma el enqueue de un lote
- **THEN** existe un registro append-only con `accion = "COMUNICACION_ENVIAR"` y `filas_afectadas` igual a la cantidad creada o reutilizada

#### Scenario: Aprobar comunicación queda auditado
- **WHEN** un usuario con `comunicacion:aprobar` aprueba un lote o comunicación
- **THEN** existe un registro append-only con `accion = "COMUNICACION_APROBAR"`

#### Scenario: Cancelar comunicación queda auditado
- **WHEN** un usuario autorizado cancela un lote o comunicación
- **THEN** existe un registro append-only con `accion = "COMUNICACION_CANCELAR"`

#### Scenario: Auditoría no expone destinatario
- **WHEN** se audita cualquier acción de comunicaciones
- **THEN** el campo `detalle` no contiene email ni destinatario en texto plano

