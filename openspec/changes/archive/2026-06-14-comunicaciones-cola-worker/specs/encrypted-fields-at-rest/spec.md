## ADDED Requirements

### Requirement: Destinatario de comunicacion cifrado en reposo
El sistema SHALL almacenar `Comunicacion.destinatario` cifrado en reposo usando la utilidad AES-256 existente.

- La base de datos MUST persistir solo ciphertext para el destinatario.
- Repositories y logs MUST NOT exponer el destinatario en plaintext salvo en el punto mínimo necesario para el proveedor de envío.
- Las respuestas API MUST evitar devolver destinatario completo en plaintext; si se requiere visualización, MUST usar representación enmascarada.

#### Scenario: Destinatario persistido no es plaintext
- **WHEN** se crea una comunicación para `alumno@example.edu`
- **THEN** el valor persistido en `destinatario` difiere del email original y no revela el plaintext

#### Scenario: API no devuelve destinatario completo
- **WHEN** un usuario consulta el estado de comunicaciones
- **THEN** la respuesta no contiene el email completo en plaintext

#### Scenario: Logs no contienen destinatario plaintext
- **WHEN** ocurre un error de envío para una comunicación
- **THEN** los logs estructurados incluyen ids/estado pero no el destinatario en plaintext
