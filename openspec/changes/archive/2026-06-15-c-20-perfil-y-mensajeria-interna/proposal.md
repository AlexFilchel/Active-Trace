# Proposal — C-20 perfil-y-mensajeria-interna

## Why

Los usuarios del sistema no tienen forma de ver ni editar sus propios datos de perfil (nombre, datos bancarios, regional) sin pasar por ADMIN, ni de comunicarse entre sí dentro de la plataforma. C-07 construyó el modelo `Usuario` y los endpoints de gestión (ADMIN), pero omitió deliberadamente los endpoints de autogestión y la mensajería inter-usuario (inbox).

## What Changes

- **Nuevo endpoint de perfil propio** (`GET /api/perfil`, `PATCH /api/perfil`): cualquier usuario autenticado puede ver y editar sus datos editables (nombre, datos bancarios cifrados, regional, legajo_profesional, facturador). CUIL es de solo lectura. No requiere permiso especial — opera sobre la identidad de la sesión.
- **Nuevos modelos de mensajería interna**: `HiloMensaje` (conversación entre dos o más usuarios registrados) y `MensajeInterno` (cada mensaje dentro del hilo). Incluye los endpoints `/api/inbox/*`.
- **Inbox**: listar hilos propios, leer mensajes de un hilo, responder dentro del hilo, marcar como leído.
- **Envío de mensajes**: cualquier usuario autenticado puede iniciar un hilo o responder; se valida que destinatario y remitente estén en el mismo tenant.
- F11.3 (cierre de sesión) ya está implementado en C-03; no requiere trabajo adicional.

## Capabilities

### New Capabilities

- `perfil-propio`: ver y editar el propio perfil de usuario (campos editables / solo lectura, PII cifrado)
- `mensajeria-interna`: inbox de hilos, lectura de mensajes, respuesta y envío entre usuarios del mismo tenant

### Modified Capabilities

_(ninguna — `usuarios-y-asignaciones` mantiene su spec sin cambios; los nuevos endpoints son un scope distinto)_

## Impact

- **Modelos nuevos**: `HiloMensaje`, `MensajeInterno` en `app/models/mensajeria.py`
- **Migración nueva**: tabla `hilo_mensaje` y `mensaje_interno`
- **Routers nuevos**: `app/api/v1/routers/perfil.py`, `app/api/v1/routers/inbox.py`
- **Schemas nuevos**: `app/schemas/perfil.py`, `app/schemas/mensajeria.py`
- **Sin cambios** al modelo `Usuario` existente — solo nuevos endpoints que lo leen/actualizan
- **Cifrado**: CBU y alias_cbu se leen/escriben con AES-256 (ya implementado en C-07)
- **No modifica** ningún spec existente
