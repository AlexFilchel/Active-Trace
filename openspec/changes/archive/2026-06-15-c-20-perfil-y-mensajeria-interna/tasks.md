# Tasks — C-20 perfil-y-mensajeria-interna

## 1. Migración y modelos de mensajería

- [x] 1.1 Crear `app/models/mensajeria.py` con `HiloMensaje` y `MensajeInterno` (TenantScopedMixin, soft delete, FKs a `usuario.id`, índice en `(tenant_id, destinatario_id, leido)`)
- [x] 1.2 Crear migración Alembic `0NN_mensajeria_interna.py`: tables `hilo_mensaje` y `mensaje_interno` con FKs y constraint checks (no self-message a nivel app, no a nivel DB por ahora)
- [x] 1.3 Registrar los modelos en `app/models/__init__.py` para que Alembic los detecte

## 2. Schemas de mensajería

- [x] 2.1 Crear `app/schemas/mensajeria.py`: `CrearHiloRequest` (asunto, destinatario_id, cuerpo), `ResponderHiloRequest` (destinatario_id, cuerpo), `HiloMensajeResponse` (id, asunto, creado_por, ultimo_mensaje, mensajes_no_leidos, created_at), `MensajeInternoResponse` (id, hilo_id, remitente_id, destinatario_id, cuerpo, leido, sent_at)

## 3. Repository y service de mensajería

- [x] 3.1 Crear `app/repositories/mensajeria.py`: `HiloMensajeRepository` (listar hilos por destinatario + conteo no leídos, get hilo verificando participación) y `MensajeInternoRepository` (listar por hilo, crear, marcar leídos)
- [x] 3.2 Crear `app/services/mensajeria_service.py`: `MensajeriaService` con métodos `crear_hilo()`, `listar_hilos()`, `listar_mensajes()` (+ marcar leídos), `responder()` — valida destinatario en mismo tenant, valida no self-message, valida participación para leer

## 4. Router de inbox

- [x] 4.1 Crear `app/api/v1/routers/inbox.py`: `POST /api/inbox/hilos` (201), `GET /api/inbox/hilos` (200, lista), `GET /api/inbox/hilos/{hilo_id}/mensajes` (200, marca leído), `POST /api/inbox/hilos/{hilo_id}/mensajes` (201)
- [x] 4.2 Registrar `inbox_router` en `app/main.py`

## 5. Schemas y endpoint de perfil propio

- [x] 5.1 Crear `app/schemas/perfil.py`: `PerfilResponse` (todos los campos del usuario con PII en plaintext), `PerfilUpdateRequest` (campos editables: nombre, apellidos, banco, cbu, alias_cbu, regional, legajo_profesional, facturador — sin cuil)
- [x] 5.2 Crear `app/api/v1/routers/perfil.py`: `GET /api/perfil` (resuelve usuario desde `auth_user_id`, descifra PII, 404 si no hay usuario), `PATCH /api/perfil` (actualiza campos editables, cifra cbu/alias_cbu, ignora cuil si se envía)
- [x] 5.3 Registrar `perfil_router` en `app/main.py`

## 6. Permiso inbox en seeds

- [x] 6.1 Verificar que no se requiere permiso adicional para perfil e inbox (solo autenticación) — documentar en el router con comentario inline si aplica

## 7. Tests TDD

- [x] 7.1 `tests/test_perfil_tdd.py`: GET /api/perfil retorna PII en claro, PATCH actualiza banco/cbu, CUIL no se modifica aunque esté en payload, 404 sin usuario, aislamiento (usuario A no puede ver perfil de B con este endpoint)
- [x] 7.2 `tests/test_mensajeria_tdd.py`: crear hilo (201), destinatario otro tenant → 404, self-message → 422, listar hilos (solo los propios), leer mensajes → marca leído, responder → 201, no participante → 403, aislamiento tenant
