## 1. Contratos y pruebas RED

- [x] 1.1 Escribir tests RED de máquina de estados: transiciones válidas e inválidas.
- [x] 1.2 Escribir tests RED de preview obligatorio y hash/referencia requerida antes de enqueue.
- [x] 1.3 Escribir tests RED de enqueue masivo con `lote_id`, idempotencia y tenant isolation.
- [x] 1.4 Escribir tests RED de aprobación por lote e individual con `comunicacion:aprobar`.
- [x] 1.5 Escribir tests RED de cancelación permitida/prohibida según estado.
- [x] 1.6 Escribir tests RED de cifrado de `destinatario` sin plaintext persistido/logueado.
- [x] 1.7 Escribir tests RED de worker `Pendiente → Enviando → Enviado/Error` con DB real/efímera.

## 2. Persistencia y RBAC

- [x] 2.1 Crear modelo SQLAlchemy `Comunicacion` con `tenant_id`, soft delete, índices y enums.
- [x] 2.2 Crear migración Alembic `comunicacion` y seeds idempotentes de permisos/eventos.
- [x] 2.3 Crear repository tenant-scoped; ninguna query sin filtro de tenant.
- [x] 2.4 Ejecutar GREEN mínimo para persistencia y cifrado.

## 3. Servicios y API

- [x] 3.1 Crear DTOs Pydantic v2 con `ConfigDict(extra='forbid')`.
- [x] 3.2 Implementar service de plantillas/preview y validación de variables.
- [x] 3.3 Implementar service de enqueue, aprobación, cancelación y estado sin SQL directo.
- [x] 3.4 Crear routers `/api/comunicaciones/*` con guards `comunicacion:enviar` y `comunicacion:aprobar`.
- [x] 3.5 Registrar auditoría en acciones significativas.

## 4. Worker y endurecimiento

- [x] 4.1 Implementar worker async con lock transaccional, idempotency key y retry seguro.
- [x] 4.2 Impedir cancelación de mensajes `Enviando` y omitir cancelados en el worker.
- [x] 4.3 Agregar logs estructurados sin PII y métricas básicas.
- [x] 4.4 Triangulate: agregar casos multi-tenant, aprobación desactivada y errores de proveedor.
- [x] 4.5 Refactor: separar archivos <500 LOC y mantener flujo Router→Service→Repository→Model.

## 5. Evidencia de apply

- [x] 5.1 Completar tabla RED→GREEN→TRIANGULATE→REFACTOR en resumen de apply.
- [x] 5.2 Validar cobertura mínima: ≥80% líneas, ≥90% reglas de negocio.
- [x] 5.3 Confirmar checkpoint humano antes de habilitar side effects de envío real.
