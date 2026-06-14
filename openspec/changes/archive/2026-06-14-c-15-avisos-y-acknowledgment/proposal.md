# Proposal: C-15 — Avisos y Acknowledgment

## Why

La plataforma carece de un canal institucional para que coordinadores y administradores comuniquen alertas, novedades y avisos obligatorios al cuerpo docente y alumnado. Sin este módulo no hay forma de notificar eventos críticos (cambios de aula, suspensiones, plazos) de manera segmentada, con ventana de vigencia controlada ni confirmación de lectura auditable.

## What Changes

- Nuevo modelo `Aviso`: alcance (Global/PorMateria/PorCohorte/PorRol), severidad (Info/Advertencia/Crítico), título, cuerpo, ventana de vigencia (`inicio_en`/`fin_en`), orden de prioridad, estado activo y flag `requiere_ack`.
- Nuevo modelo `AcknowledgmentAviso`: registro de acuse de recibo por usuario; los contadores se derivan, no se denormalizan.
- Migración `012_avisos_acknowledgment`: tablas `aviso` y `acknowledgment_aviso`; seed de permiso `avisos:publicar` para COORDINADOR y ADMIN.
- Endpoints `/api/avisos/`:
  - Gestión (COORDINADOR/ADMIN): crear, editar, desactivar, listar con métricas de acks.
  - Visualización (todos los roles): listar mis avisos activos y vigentes según alcance/rol/cohorte/materia.
  - Confirmación (todos los roles): acusar recibo de un aviso que lo requiere.
- Filtrado por RN-18 (ventana de vigencia), RN-19 (requiere_ack), RN-20 (segmentación por audiencia).

## Capabilities

### New Capabilities

- `avisos-y-acknowledgment`: ABM de avisos institucionales segmentados con ventana de vigencia, filtrado por audiencia (alcance/rol/cohorte/materia), confirmación de lectura y métricas de adopción.

### Modified Capabilities

*(ninguna — módulo nuevo)*

## Impact

- **Nuevos archivos**: `backend/app/models/avisos.py`, `backend/app/schemas/avisos.py`, `backend/app/repositories/avisos.py`, `backend/app/services/aviso_service.py`, `backend/app/api/v1/routers/avisos.py`, `backend/alembic/versions/012_avisos_acknowledgment.py`.
- **Modificados**: `backend/app/models/__init__.py`, `backend/app/main.py`.
- **Dependencia**: C-06 (estructura académica — Materia, Cohorte, Rol existen en DB).
- **Sin breaking changes** en módulos existentes.
