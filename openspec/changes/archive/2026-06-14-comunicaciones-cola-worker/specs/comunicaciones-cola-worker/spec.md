## ADDED Requirements

### Requirement: Ciclo de vida de Comunicacion
El sistema SHALL mantener comunicaciones salientes con estados `Pendiente`, `Enviando`, `Enviado`, `Error` y `Cancelado`, aplicando transiciones válidas de forma centralizada en services.

- Las transiciones permitidas MUST ser: creación a `Pendiente`, `Pendiente → Enviando`, `Enviando → Enviado`, `Enviando → Error`, `Pendiente → Cancelado`.
- Toda otra transición MUST ser rechazada sin modificar el registro.
- Toda operación MUST estar acotada por `tenant_id` desde sesión o contexto interno confiable del worker.

#### Scenario: Worker inicia despacho de pendiente
- **WHEN** una comunicación `Pendiente` aprobada es tomada por el worker
- **THEN** el sistema la transiciona a `Enviando` antes de ejecutar el side effect de envío

#### Scenario: Transición inválida desde enviado es rechazada
- **WHEN** se intenta transicionar una comunicación `Enviado` a `Pendiente`
- **THEN** el sistema rechaza la operación y conserva el estado `Enviado`

#### Scenario: Cancelación solo desde pendiente
- **WHEN** se cancela una comunicación en estado `Pendiente`
- **THEN** el sistema la transiciona a `Cancelado`

#### Scenario: Cancelación durante envío es rechazada
- **WHEN** se intenta cancelar una comunicación en estado `Enviando`
- **THEN** el sistema rechaza la cancelación y conserva el estado `Enviando`

---

### Requirement: Preview obligatorio antes de encolar
El sistema SHALL generar una vista previa del asunto y cuerpo personalizado antes de crear cualquier comunicación en cola.

- El preview MUST resolver variables de plantilla con datos autorizados del destinatario y materia.
- El enqueue MUST requerir una referencia o huella válida del preview generado para el mismo tenant, actor, plantilla y destinatarios.
- Si el preview falta, expiró o no coincide, el enqueue MUST ser rechazado.

#### Scenario: Preview personaliza el contenido
- **WHEN** un usuario con `comunicacion:enviar` solicita preview para un alumno y plantilla con variables
- **THEN** el sistema retorna asunto y cuerpo con variables sustituidas para ese destinatario

#### Scenario: Enqueue sin preview falla
- **WHEN** un usuario intenta encolar comunicaciones sin referencia válida de preview
- **THEN** el sistema rechaza la operación y no crea comunicaciones `Pendiente`

---

### Requirement: Enqueue masivo e idempotencia por lote
El sistema SHALL crear comunicaciones individuales agrupadas por `lote_id` para envíos masivos.

- Cada comunicación MUST tener UUID interno, `tenant_id`, `enviado_por`, `materia_id`, `destinatario` cifrado, asunto, cuerpo, estado y `lote_id`.
- Reintentar el mismo enqueue con la misma clave de idempotencia MUST NOT duplicar destinatarios del lote.
- PROFESOR/TUTOR MUST operar solo dentro de su alcance autorizado; COORDINADOR/ADMIN MUST operar dentro del tenant.

#### Scenario: Envío masivo crea lote
- **WHEN** un usuario autorizado confirma el envío a tres alumnos después del preview
- **THEN** el sistema crea tres comunicaciones `Pendiente` con el mismo `lote_id`

#### Scenario: Reintento idempotente no duplica
- **WHEN** se repite la misma solicitud de enqueue con la misma clave de idempotencia
- **THEN** el sistema retorna el lote existente sin crear comunicaciones duplicadas

#### Scenario: Tenant isolation en enqueue
- **WHEN** un usuario del tenant A intenta incluir un destinatario del tenant B
- **THEN** el sistema rechaza o ignora ese destinatario y no expone datos del tenant B

---

### Requirement: Aprobación humana configurable por tenant
El sistema SHALL respetar una configuración por tenant que determina si un envío requiere aprobación humana antes de despacho.

- Si la aprobación está activa, las comunicaciones MUST permanecer no despachables hasta aprobación.
- La aprobación por lote o individual MUST requerir `comunicacion:aprobar`.
- La ausencia o ambigüedad de configuración para envíos masivos MUST resolverse fail-safe requiriendo aprobación.

#### Scenario: Lote requiere aprobación antes del worker
- **WHEN** el tenant tiene aprobación activa y se encola un lote
- **THEN** el worker no despacha sus comunicaciones hasta que sean aprobadas

#### Scenario: Aprobación por lote habilita despacho
- **WHEN** un usuario con `comunicacion:aprobar` aprueba un lote pendiente
- **THEN** todas las comunicaciones pendientes del lote quedan habilitadas para despacho

#### Scenario: Aprobación individual habilita solo un destinatario
- **WHEN** un usuario con `comunicacion:aprobar` aprueba una comunicación individual de un lote
- **THEN** solo esa comunicación queda habilitada para despacho

#### Scenario: Usuario sin permiso no aprueba
- **WHEN** un usuario sin `comunicacion:aprobar` intenta aprobar un lote
- **THEN** el sistema retorna HTTP 403 y no habilita despacho

---

### Requirement: APIs de comunicaciones seguras
El sistema SHALL exponer endpoints bajo `/api/comunicaciones/*` protegidos por permisos finos y alcance de sesión.

- Preview, enqueue, cancelación propia permitida y consulta operativa MUST requerir `comunicacion:enviar`.
- Aprobación MUST requerir `comunicacion:aprobar`.
- La identidad, actor y tenant MUST derivarse exclusivamente de la sesión/JWT verificado, nunca del body, path, query o headers.
- Los DTOs request/response MUST rechazar campos extra.

#### Scenario: Usuario con permiso genera preview
- **WHEN** un usuario con `comunicacion:enviar` llama al endpoint de preview
- **THEN** el sistema procesa la solicitud dentro del tenant y alcance autorizados

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario autenticado sin `comunicacion:enviar` llama a `/api/comunicaciones/preview`
- **THEN** el sistema retorna HTTP 403

#### Scenario: Body no puede suplantar identidad
- **WHEN** el body incluye `tenant_id` o `enviado_por` ajenos a la sesión
- **THEN** el sistema ignora/rechaza esos campos y nunca los usa como identidad

---

### Requirement: Worker de despacho idempotente
El sistema SHALL proveer un worker async que consume comunicaciones despachables de forma segura e idempotente.

- El worker MUST seleccionar comunicaciones con lock transaccional para evitar procesamiento concurrente doble.
- El worker MUST omitir comunicaciones `Cancelado`, no aprobadas o fuera del tenant/contexto permitido.
- Ante éxito MUST transicionar `Enviando → Enviado` y completar `enviado_at`.
- Ante error MUST transicionar a `Error` o dejar reintento controlado según política documentada, sin perder trazabilidad.

#### Scenario: Worker procesa pendiente aprobada con éxito
- **WHEN** existe una comunicación `Pendiente` aprobada y el proveedor confirma envío
- **THEN** el worker la transiciona `Pendiente → Enviando → Enviado` y registra `enviado_at`

#### Scenario: Worker registra error de proveedor
- **WHEN** el proveedor de envío falla para una comunicación `Enviando`
- **THEN** el worker registra el error de forma controlada sin PII y deja el estado `Error` o reintento según política

#### Scenario: Worker no envía canceladas
- **WHEN** una comunicación está `Cancelado`
- **THEN** el worker no ejecuta side effect de envío para esa comunicación

---

### Requirement: Auditoría de acciones de comunicaciones
El sistema SHALL auditar acciones significativas de comunicaciones con actor real, tenant, materia/lote y cantidad de registros afectados.

- Enqueue/confirmación de envío MUST auditar `COMUNICACION_ENVIAR`.
- Aprobación MUST auditar `COMUNICACION_APROBAR`.
- Cancelación MUST auditar `COMUNICACION_CANCELAR`.
- El detalle de auditoría MUST NOT incluir destinatarios en plaintext.

#### Scenario: Enqueue audita comunicación enviar
- **WHEN** un usuario confirma un lote de comunicaciones
- **THEN** el sistema registra `COMUNICACION_ENVIAR` con actor, tenant, lote y filas afectadas

#### Scenario: Aprobación audita aprobación
- **WHEN** un aprobador aprueba un lote o comunicación individual
- **THEN** el sistema registra `COMUNICACION_APROBAR` sin exponer destinatarios en plaintext

#### Scenario: Cancelación audita cancelación
- **WHEN** un usuario autorizado cancela una comunicación o lote pendiente
- **THEN** el sistema registra `COMUNICACION_CANCELAR` con el alcance afectado
