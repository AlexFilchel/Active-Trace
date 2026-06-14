## Context

C-11 ya entrega alumnos atrasados. C-12 agrega el canal saliente: mensajes personalizados a alumnos, agrupados por `lote_id`, con PII cifrada, cola asincrónica, aprobación opcional por tenant y auditoría. Reglas duras: identidad solo desde JWT, repositorios con `tenant_id`, routers sin negocio, services sin SQL, RBAC fail-closed.

## Goals / Non-Goals

**Goals:**
- Implementar `Comunicacion` como registro auditable, tenant-scoped y con destinatario cifrado.
- Exponer preview, enqueue, approve, cancel y status/listado con DTOs Pydantic `extra='forbid'`.
- Despachar con worker idempotente: `Pendiente → Enviando → Enviado/Error`, cancelación solo segura.
- Registrar eventos `COMUNICACION_ENVIAR`, `COMUNICACION_APROBAR`, `COMUNICACION_CANCELAR`.

**Non-Goals:**
- Bandeja interna F3.4, tablón de avisos F3.5, UI frontend completa, N8N avanzado o proveedor real definitivo si no existe cliente saliente.

## Decisions

1. **Cola DB-backed inicial.** El worker toma filas `Pendiente` aprobadas con lock transaccional/skip-locked. Alternativa: broker externo. Razón: menor superficie y coherencia con auditoría/tenant.
2. **State machine en Service.** Transiciones válidas centralizadas; repositories solo persisten/leen. Alternativa: lógica en router/worker. Rechazada por Clean Architecture.
3. **Aprobación como metadatos por fila/lote.** `requiere_aprobacion`, `aprobado_at`, `aprobado_por`, `cancelado_at`, `cancelado_por`, `error_detalle`, `intentos`. Alternativa: tabla lote separada. Diferir hasta que reporting de lotes lo requiera.
4. **Preview token/huella.** Enqueue requiere referencia o hash del preview generado para mismo actor/tenant/destinatarios/plantilla. Evita encolar sin vista previa.
5. **Side effects después de transición.** Worker marca `Enviando` antes de llamar proveedor; si falla, incrementa intentos y termina `Error` o reintento según política.

## Risks / Trade-offs

- Envío duplicado por retry → transición atómica, idempotency key por comunicación y lock de fila.
- PII en logs/excepciones → logs solo con ids/lote/estado; destinatario siempre cifrado en reposo.
- Aprobación omitida por configuración mal resuelta → tenant config leída server-side, default fail-safe: requiere aprobación para envíos masivos si no hay config clara.
- Cancelar mientras worker procesa → cancelación permitida solo en `Pendiente`; `Enviando` no se cancela, se observa resultado.

## Migration Plan

1. Crear migración `comunicacion` con índices `(tenant_id, estado)`, `(tenant_id, lote_id)`, `(tenant_id, materia_id)` y campos de auditoría/soft delete.
2. Seed idempotente de permisos/eventos.
3. Desplegar API sin habilitar worker real; correr tests.
4. Activar worker con proveedor stub/configurado y observabilidad.
5. Rollback: detener worker, revertir rutas/servicios y migración si no hay datos productivos; si hay datos, preservar tabla y deshabilitar enqueue.

## Governance / Checkpoint

Dominio ALTO. Antes de apply se requiere aprobación humana explícita para código que: cifra/descifra `destinatario`, invoca proveedor externo, cambia política de aprobación o procesa comunicaciones reales.

## Open Questions

- Proveedor inicial: SMTP/N8N/stub local.
- Umbral exacto de “masivo” por tenant si la config no lo define aún.
