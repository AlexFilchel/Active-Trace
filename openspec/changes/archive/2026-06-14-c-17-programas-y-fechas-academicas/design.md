# Design: C-17 — Programas y Fechas Académicas

## Context

Este módulo agrega dos entidades de soporte académico al sistema: los programas oficiales de las materias (documentos) y las fechas de instancias evaluativas. Ambas son de **governance BAJO** — operaciones CRUD simples sin lógica de negocio compleja.

Dependencias: `C-06 estructura-academica` (FK a `materia`, `carrera`, `cohorte`). Ambas entidades heredan `TenantScopedMixin`.

El permiso `estructura:gestionar` ya existe en la DB (seedeado en C-06, asignado a COORDINADOR y ADMIN). No requiere nuevo permiso.

## Goals / Non-Goals

**Goals:**
- CRUD de `ProgramaMateria` con referencia de archivo opaca.
- CRUD de `FechaAcademica` con máquina de tipos (Parcial/TP/Coloquio/Recuperatorio).
- Filtros por materia, cohorte, carrera, tipo y período.
- Generación de fragmento LMS: texto formateado listo para el aula virtual.
- Auditoría en crear y editar.

**Non-Goals:**
- Upload real de archivos (la referencia es opaca — el almacenamiento es externo).
- Notificaciones al crear/editar fechas (depende de C-11).
- Vista de calendario visual en el backend (es responsabilidad del frontend).
- Validación de solapamiento de fechas evaluativas entre materias.

## Decisions

### D1 — `referencia_archivo` como campo opaco (String)
**Decisión**: `referencia_archivo` almacena una URL o path externo como texto sin validación de formato. El servicio de almacenamiento (S3, filesystem, etc.) es responsabilidad del cliente que llama a la API.

**Alternativa descartada**: campo con validación de URL (acoplamiento al tipo de almacenamiento).

### D2 — `estructura:gestionar` reutilizado (sin nuevo permiso)
**Decisión**: se reutiliza el permiso existente `estructura:gestionar` (ya seedeado para COORDINADOR/ADMIN en C-06). No se crean nuevos permisos.

**Rationale**: los programas y fechas académicas son parte de la estructura académica — no ameritan un permiso propio en MVP.

### D3 — Fragmento LMS como endpoint dedicado (no campo calculado)
**Decisión**: `GET /api/fechas-academicas/fragmento-lms?materia_id=&cohorte_id=&periodo=` devuelve `{ "texto": "..." }`. El texto lista por tipo e instancia con formato markdown simple.

**Alternativa descartada**: campo calculado en el response de listado (inflación del payload para todos los listados).

**Formato del fragmento**:
```
**Fechas de evaluación — [Materia] — [Período]**

📅 1er Parcial: DD/MM/YYYY — [título]
📅 2do Parcial: DD/MM/YYYY — [título]
📅 TP 1: DD/MM/YYYY — [título]
📅 Coloquio 1: DD/MM/YYYY — [título]
```

### D4 — Ruta `/fragmento-lms` registrada BEFORE `/{id}`
**Decisión**: igual que `/mis-tareas` en C-16, el endpoint estático debe registrarse antes del paramétrico `/{id}` en el router FastAPI.

### D5 — Índices para filtros frecuentes
Índices en:
- `ix_programa_materia_tenant_id` (mixin)
- `ix_programa_materia_materia_id`
- `ix_programa_materia_carrera_id`
- `ix_programa_materia_cohorte_id`
- `ix_fecha_academica_tenant_id` (mixin)
- `ix_fecha_academica_materia_id`
- `ix_fecha_academica_cohorte_id`
- `ix_fecha_academica_tipo`

## Migration Plan

1. Migración `014_programas_fechas_academicas`: crea `programa_materia` y `fecha_academica` con FKs e índices.
2. Sin seed de permisos (reutiliza `estructura:gestionar`).
3. Sin downtime (tablas nuevas, sin ALTER en existentes).
4. Rollback: `downgrade` dropea ambas tablas.

## Risks / Trade-offs

- **`referencia_archivo` opaco**: si el archivo externo se borra, la referencia queda huérfana. Mitigación: soft-delete preserva la referencia en historial.
- **Sin validación de duplicados**: dos programas distintos pueden apuntar al mismo materia×carrera×cohorte. Mitigación: el listado filtra por esos tres campos, el frontend muestra todos.
