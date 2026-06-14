## Why

C-12 habilita el flujo central posterior al análisis de atrasados: generar comunicaciones salientes a alumnos con trazabilidad, cola asíncrona y control humano cuando el tenant lo exige. Hoy existe análisis (C-11), pero falta el mecanismo seguro para previsualizar, encolar, aprobar, cancelar y despachar mensajes sin exponer PII.

## What Changes

- Agrega modelo `Comunicacion` multi-tenant con destinatario cifrado, `lote_id` y estados `Pendiente`, `Enviando`, `Enviado`, `Error`, `Cancelado`.
- Agrega preview obligatorio de asunto/cuerpo con variables de plantilla antes de encolar.
- Agrega APIs `/api/comunicaciones/*` con identidad desde sesión y guard `comunicacion:enviar`.
- Agrega aprobación configurable por tenant, por lote o individual, con guard `comunicacion:aprobar`.
- Agrega worker async idempotente para despacho, retry seguro, cancelación y auditoría.
- Agrega eventos de auditoría para envío/aprobación/cancelación.

## Capabilities

### New Capabilities
- `comunicaciones-cola-worker`: ciclo de vida completo de comunicaciones salientes, preview, cola, aprobación, cancelación, worker y contratos API.

### Modified Capabilities
- `rbac`: incorpora permisos `comunicacion:enviar` y `comunicacion:aprobar` al catálogo/seed/matriz por tenant.
- `audit-log`: incorpora eventos `COMUNICACION_ENVIAR`, `COMUNICACION_APROBAR` y `COMUNICACION_CANCELAR`.
- `encrypted-fields-at-rest`: exige cifrado AES-256 para `Comunicacion.destinatario` y prohíbe persistencia/logs en texto plano.

## Impact

- Backend: `backend/app/{models,schemas,repositories,services,api/v1/routers,workers}/`.
- DB: migración Alembic `comunicacion` + permisos/eventos necesarios.
- Seguridad: dominio ALTO; apply requiere checkpoint humano antes de tocar PII cifrada o side effects de envío real.
- Testing: pytest con DB real/efímera; TDD estricto con evidencia RED→GREEN→TRIANGULATE→REFACTOR.
