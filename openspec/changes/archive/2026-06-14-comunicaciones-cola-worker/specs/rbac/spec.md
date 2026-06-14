## ADDED Requirements

### Requirement: Permisos de comunicaciones salientes
El sistema SHALL incorporar permisos finos para comunicaciones salientes al catálogo RBAC por tenant.

- `comunicacion:enviar` MUST proteger preview, enqueue, cancelación permitida y consulta operativa de comunicaciones.
- `comunicacion:aprobar` MUST proteger aprobación por lote e individual.
- La semilla de permisos MUST ser idempotente y scoped por tenant.

#### Scenario: Permiso comunicacion enviar existe por tenant
- **WHEN** se ejecuta la migración/seed de C-12 en un tenant existente
- **THEN** el catálogo del tenant contiene `comunicacion:enviar` sin duplicados

#### Scenario: Permiso comunicacion aprobar existe por tenant
- **WHEN** se ejecuta la migración/seed de C-12 en un tenant existente
- **THEN** el catálogo del tenant contiene `comunicacion:aprobar` sin duplicados

#### Scenario: Endpoint de aprobación falla cerrado
- **WHEN** un usuario no posee `comunicacion:aprobar` y llama a aprobar lote
- **THEN** el sistema retorna HTTP 403 y no modifica comunicaciones
