## ADDED Requirements

### Requirement: Vista previa de comunicación

El sistema SHALL obtener una vista previa del mensaje a enviar a los alumnos atrasados mediante `POST /api/comunicaciones/preview` con `comision_id` y `tipo`, mostrando asunto y cuerpo antes de cualquier envío.

#### Scenario: Se muestra la vista previa

- **WHEN** el PROFESOR solicita la vista previa para una comisión y un tipo de comunicación
- **THEN** el sistema muestra el asunto y el cuerpo del mensaje tal como lo recibirá el destinatario

#### Scenario: La vista previa falla

- **WHEN** `POST /api/comunicaciones/preview` responde con error
- **THEN** el sistema muestra un mensaje de error y deshabilita el botón de envío

### Requirement: Envío masivo de comunicaciones

El sistema SHALL permitir el envío masivo a los alumnos atrasados mediante `POST /api/comunicaciones/enviar` con `comision_id`, `tipo` y un `mensaje_personalizado` opcional, solo después de que el PROFESOR confirme la vista previa.

#### Scenario: Envío confirmado

- **WHEN** el PROFESOR confirma el envío tras revisar la vista previa
- **THEN** el sistema envía `POST /api/comunicaciones/enviar` y muestra que los mensajes ingresaron a la cola en estado Pendiente

#### Scenario: Envío con mensaje personalizado

- **WHEN** el PROFESOR agrega un mensaje personalizado y confirma
- **THEN** el sistema incluye `mensaje_personalizado` en la petición de envío

#### Scenario: El envío no puede ejecutarse sin vista previa

- **WHEN** no se ha generado una vista previa válida
- **THEN** el botón de envío permanece deshabilitado

### Requirement: Tracking del estado de la cola en tiempo real

El sistema SHALL mostrar el estado de cada comunicación obtenido desde `GET /api/comunicaciones/estado?comision_id=`, refrescándolo periódicamente, y reflejar las transiciones Pendiente → Enviando → OK / Fallido / Cancelado.

#### Scenario: Se muestran los estados de la cola

- **WHEN** existen comunicaciones en la cola de la comisión
- **THEN** el sistema muestra cada destinatario con su estado actual (Pendiente, Enviando, OK, Fallido o Cancelado)

#### Scenario: Refresco periódico del estado

- **WHEN** el panel de tracking está visible y el estado cambia en el backend de Pendiente a OK
- **THEN** el sistema vuelve a consultar el estado periódicamente y refleja el nuevo estado sin recargar la página

#### Scenario: No hay comunicaciones en la cola

- **WHEN** la respuesta de estado es una lista vacía
- **THEN** el sistema muestra un estado informativo "Sin comunicaciones"
