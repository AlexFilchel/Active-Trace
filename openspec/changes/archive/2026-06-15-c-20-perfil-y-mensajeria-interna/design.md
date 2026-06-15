# Design — C-20 perfil-y-mensajeria-interna

## Context

C-07 construyó `Usuario` con campos PII cifrados y los endpoints de administración (`/api/admin/usuarios`). Esos endpoints requieren `usuarios:gestionar` (solo ADMIN). Lo que falta es:

1. Un endpoint de autogestión donde cada usuario autenticado pueda ver y editar su propio perfil sin requerir permisos de administración.
2. Una capa de mensajería interna (inbox) que permita a usuarios registrados intercambiar mensajes dentro del sistema, separada del sistema de emails a alumnos (C-12).

El modelo de cifrado ya está implementado en `app/core/encryption.py`. El logout ya existe desde C-03.

## Goals / Non-Goals

**Goals:**
- Endpoint `/api/perfil` para lectura y escritura del perfil propio (identidad desde JWT)
- Modelos `HiloMensaje` + `MensajeInterno` con endpoints `/api/inbox/*`
- CUIL no modificable por el propio usuario (solo ADMIN puede tocarlo)
- PII decifrada en respuesta del perfil propio (es el propio usuario quien pide sus datos)
- Aislamiento tenant en mensajería (no se puede enviar mensajes fuera del propio tenant)

**Non-Goals:**
- Notificaciones push / WebSocket en tiempo real
- Archivos adjuntos en mensajes
- Mensajería con alumnos (eso es Comunicaciones, C-12)
- Modificar CUIL desde este endpoint (ADMIN-only via `/api/admin/usuarios/{id}`)

## Decisions

### D1 — Perfil sin permiso especial, identidad desde JWT

El endpoint `GET /api/perfil` y `PATCH /api/perfil` no requieren ningún permiso `modulo:accion` más allá de autenticación (`get_current_user`). La identidad proviene del JWT (`user.user_id` → `auth_user.id` → `usuario.auth_user_id`). No se acepta ningún `usuario_id` en el payload.

**Alternativa descartada**: requerir `perfil:ver` / `perfil:editar` como permisos. Innecesario — todos los usuarios autenticados deben poder ver/editar su propio perfil.

### D2 — Perfil retorna PII decifrada

A diferencia de los endpoints de admin (que devuelven los campos cifrados o los omiten), el endpoint de perfil propio DEBE descifrar y retornar los valores en plaintext al usuario autenticado. Es el propio usuario pidiendo sus propios datos.

### D3 — CUIL inmutable desde perfil

`cuil` está excluido de `PerfilUpdateRequest`. Si el cliente envía `cuil`, el campo es ignorado silenciosamente (no error 422). Solo ADMIN puede modificar CUIL desde `/api/admin/usuarios/{id}`.

### D4 — Modelo de mensajería: hilo + mensajes

```
HiloMensaje {
  id           : UUID
  tenant_id    : UUID
  asunto       : texto
  creado_por   : UUID  → usuario.id
  created_at   : datetime
  deleted_at   : datetime | null
}

MensajeInterno {
  id           : UUID
  tenant_id    : UUID
  hilo_id      : UUID  → hilo_mensaje.id
  remitente_id : UUID  → usuario.id
  destinatario_id : UUID → usuario.id
  cuerpo       : texto
  leido        : booleano (default false)
  sent_at      : datetime
  deleted_at   : datetime | null
}
```

**Alternativa descartada**: tabla única `MensajeInterno` con `hilo_id` auto-referencial. Separar el hilo del mensaje simplifica listar conversaciones (query a `HiloMensaje`) vs leer el contenido (query a `MensajeInterno`).

### D5 — Iniciar hilo vs responder

- `POST /api/inbox/hilos` → crea un hilo nuevo y el primer mensaje
- `POST /api/inbox/hilos/{hilo_id}/mensajes` → agrega respuesta al hilo existente
- El hilo agrupa todos los mensajes del asunto; cualquier participante puede responder.

### D6 — Sin permisos granulares para inbox

El inbox es autoservicio: cualquier usuario autenticado puede leer su propio inbox (solo ve mensajes donde es destinatario) y puede enviar mensajes a otros usuarios del mismo tenant. No se expone inbox ajeno.

## Risks / Trade-offs

- **[Riesgo] Hilos sin participantes explícitos**: El modelo actual (remitente_id + destinatario_id por mensaje) no tiene una tabla de participantes de hilo. Esto limita grupos — solo mensajes 1:1 o broadcast por respuesta. Mitigación: el scope de C-20 es básico; grupos se pueden agregar luego sin romper el modelo.
- **[Riesgo] Mensajes sin leer sin tracking por hilo**: `leido` está en cada `MensajeInterno`, no a nivel hilo. Mitigación: suficiente para el MVP — un hilo se considera "no leído" si tiene algún mensaje no leído dirigido al usuario.

## Migration Plan

```
Migración 0NN_mensajeria_interna:
  CREATE TABLE hilo_mensaje (id, tenant_id, asunto, creado_por, created_at, deleted_at)
  CREATE TABLE mensaje_interno (id, tenant_id, hilo_id, remitente_id, destinatario_id, cuerpo, leido, sent_at, deleted_at)
  FK: hilo_mensaje.tenant_id → tenant.id
  FK: mensaje_interno.hilo_id → hilo_mensaje.id
  INDEX: mensaje_interno(tenant_id, destinatario_id, leido) — optimiza listar inbox no leído
```

No hay cambios al schema de `usuario` — el PATCH de perfil solo actualiza columnas existentes.
