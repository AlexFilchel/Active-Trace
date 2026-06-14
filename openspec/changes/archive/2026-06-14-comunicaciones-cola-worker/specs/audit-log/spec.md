## ADDED Requirements

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
