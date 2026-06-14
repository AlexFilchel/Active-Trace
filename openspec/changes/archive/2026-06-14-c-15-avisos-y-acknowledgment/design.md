# Design: C-15 — Avisos y Acknowledgment

## Context

Módulo nuevo sin dependencias de código de otros cambios en progreso. Depende de entidades ya existentes: `Tenant`, `Materia`, `Cohorte`, `Usuario`, `Asignacion` (todos en DB desde C-06). El patrón de implementación es idéntico al de C-14: TenantScopedMixin + repositorios + servicio + router.

## Goals / Non-Goals

**Goals**: ABM de avisos segmentados, filtrado en tiempo real por audiencia, ventana de vigencia, ack idempotente, métricas derivadas.

**Non-Goals**: push notifications (WebSocket, email, mobile); traducción de cuerpo; versioning de avisos; avisos ad-hoc por usuario individual (eso es mensajería — C-09).

## Decisions

### D1 — Filtrado de audiencia en el servicio, no en el modelo

El `GET /api/avisos` aplica los filtros de alcance/rol/cohorte/materia en Python sobre los registros ya traídos, **no** como un query SQL con JOINs complejos. Razón: el volumen de avisos activos en un tenant es bajo (decenas, no miles); la legibilidad y testeabilidad superan la optimización prematura. Si el volumen crece, se puede mover a SQL en `AvisoRepository.list_para_usuario()` sin cambiar la interfaz.

### D2 — Asignaciones vigentes para filtrar alcance PorMateria / PorCohorte

Para determinar si un aviso `PorMateria` o `PorCohorte` es visible para el usuario, se consultan las `Asignacion` vigentes del `usuario.id` (no del `auth_user.id`). Se usa `AsignacionRepository.list_vigentes_for_user()` — ya existente. El usuario se resuelve con `UsuarioRepository.get_by_auth_user_id()` — patrón estándar del proyecto.

### D3 — Ack idempotente con unique constraint

`acknowledgment_aviso` tiene índice único `(tenant_id, aviso_id, usuario_id)`. El servicio intenta `SELECT` antes de `INSERT`; si existe → responde 200 sin error. No usar `INSERT ON CONFLICT` para mantener coherencia con el patrón del resto de repositorios.

### D4 — `rol_destino` como varchar, no FK

Los roles en el sistema son strings (`ALUMNO`, `COORDINADOR`, etc.) en `auth_user.roles` (jsonb array). No existe tabla `Rol` con registros fijos. `rol_destino` se almacena como varchar y se compara con `user.roles` del JWT.

### D5 — Migración 012: número de versión

Sigue la secuencia: `011_evaluaciones_coloquios` → `012_avisos_acknowledgment`. La migración crea ambas tablas, los índices y el seed idempotente de `avisos:publicar`.

### D6 — Sin campo `acusado` en la tabla Aviso

El campo `acusado: bool` en `AvisoResponse` se calcula en el servicio comparando si existe un `AcknowledgmentAviso` para `(aviso.id, usuario.id)`. No se almacena en la tabla.

## Structure

```
backend/app/
├── models/
│   └── avisos.py              ← Aviso, AcknowledgmentAviso
├── schemas/
│   └── avisos.py              ← Request/Response schemas (extra='forbid')
├── repositories/
│   └── avisos.py              ← AvisoRepository, AckRepository
├── services/
│   └── aviso_service.py       ← AvisoService (lógica de filtrado y ack)
├── api/v1/routers/
│   └── avisos.py              ← router prefix="/api/avisos"
└── main.py                    ← include avisos_router
alembic/versions/
└── 012_avisos_acknowledgment.py
```

## API Contract

| Método | Path | Permiso | Status |
|---|---|---|---|
| POST | `/api/avisos` | `avisos:publicar` | 201 |
| GET | `/api/avisos/gestion` | `avisos:publicar` | 200 |
| GET | `/api/avisos` | autenticado | 200 |
| PATCH | `/api/avisos/{id}` | `avisos:publicar` | 200 |
| POST | `/api/avisos/{id}/ack` | autenticado | 200/201 |
| GET | `/api/avisos/{id}/metricas` | `avisos:publicar` | 200 |

## Secuencia: GET /api/avisos (mis avisos)

```
Router → AvisoService.listar_mis_avisos(auth_user_id, roles, now)
  ↓
  1. resolve usuario_id via UsuarioRepository.get_by_auth_user_id()
  2. fetch asignaciones vigentes via AsignacionRepository.list_vigentes_for_user()
  3. AvisoRepository.list_activos_vigentes(now)  ← filtra activo=true, inicio≤now≤fin
  4. Para cada aviso:
     - evaluar audiencia (alcance/rol/materia/cohorte vs. datos del usuario)
     - evaluar ack: AckRepository.existe(aviso.id, usuario.id) → campo acusado
     - filtrar si requiere_ack=true y ya acusado (salvo incluir_acusados=true)
  5. Ordenar por orden ASC, inicio_en DESC
  6. Retornar lista AvisoResponse
```
