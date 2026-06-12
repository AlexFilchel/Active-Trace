## Context

C-09 implementó el padrón versionado de alumnos (`EntradaPadron`). C-10 añade las calificaciones: cada `Calificacion` referencia una `EntradaPadron` (el alumno en esa versión del padrón) y una actividad. El flujo tiene dos fases separadas: **preview** (sin escritura) y **confirmación** (bulk-insert). El umbral de aprobación es scope-isolated por asignación docente.

Stack: FastAPI + SQLAlchemy async + PostgreSQL. El parser reutiliza la infraestructura de `padron_parser.py` (openpyxl + csv.DictReader). Strict TDD.

## Goals / Non-Goals

**Goals**: modelos Calificacion + UmbralMateria, parser de LMS, preview + import endpoints, umbral configurable, vaciado scope-isolated, reporte de finalización.

**Non-Goals**: análisis de atrasados (C-11), exportación de reportes, frontend.

## Decisions

### D1 — `aprobado` derivado en import, no en query

`aprobado` se calcula al momento del import y se persiste como columna booleana. Alternativa: calcular `aprobado` on-the-fly en cada consulta con el umbral vigente.

**Razón**: C-11 hará millones de evaluaciones de `aprobado` para detectar atrasados y rankings. Un campo pre-computado convierte esas consultas en filtros simples `WHERE aprobado = true`. El trade-off es que si el umbral cambia después de una importación, las calificaciones antiguas tienen `aprobado` obsoleto — se resuelve documentando que cambiar el umbral sugiere re-importar.

### D2 — Scope de calificaciones: actor × materia (no versión de padrón)

Una calificación referencia `entrada_padron_id` (alumno en la versión activa del padrón al momento del import) y al actor vía `asignacion_id`. El vaciado usa `(actor_id, materia_id)` como scope.

**Razón**: RN-04 define explícitamente que el scope es `(usuario_id × materia_id)`. No usar `version_padron_id` como scope evita que un cambio de padrón borre calificaciones existentes.

### D3 — Preview es stateless (sin persistencia temporal)

El endpoint `POST /api/calificaciones/preview` analiza el archivo en memoria y devuelve la lista de actividades detectadas. No guarda nada en DB.

**Razón**: simplifica el flujo (no hay que limpiar datos temporales ni gestionar TTL). El archivo se sube de nuevo en la confirmación — overhead mínimo para archivos de calificaciones típicos (<5 MB).

### D4 — Upsert de calificaciones por `(entrada_padron_id, actividad, actor)`

Si el mismo actor importa calificaciones para una materia dos veces, los registros existentes se actualizan (upsert via `ON CONFLICT DO UPDATE`) en lugar de crear duplicados.

**Razón**: el docente puede corregir y re-exportar desde el LMS. Un error de "duplicado" sería confuso. El upsert preserva la idempotencia del import.

### D5 — UmbralMateria único por `(asignacion_id, materia_id)`

Un único registro activo de `UmbralMateria` por par asignación-materia. El PUT hace upsert.

**Razón**: simplifica el lookup en el momento del import (no hay historial de umbrales que resolver). Si se necesitara historial en el futuro, se agrega `vigente_desde`.

## Risks / Trade-offs

- **`aprobado` obsoleto tras cambio de umbral**: si el docente cambia el umbral después de importar, los datos históricos tienen `aprobado` calculado con el umbral anterior. Mitigación: documentar en el endpoint de umbral que recomienda re-importar; en C-11 el análisis usa los valores persistidos.
- **Archivo subido dos veces (preview + confirm)**: overhead de red y parsing doble. Mitigación: archivos LMS típicos son <2 MB; aceptable para UX de confirmación explícita.
- **RN-04 scope-isolated requiere `actor_id → asignacion_id`**: el JWT provee `auth_user_id`, que debe resolverse a `usuario.id` y luego a la `asignacion_id` activa para la materia. Patrón ya establecido en C-09 (`get_by_auth_user_id`). Si el docente no tiene asignación activa en la materia, retornar 403.

## Migration Plan

1. `007_calificaciones.py`: crear tablas `calificacion` y `umbral_materia`; índice único en `(tenant_id, entrada_padron_id, actividad)` para el upsert; índice en `(tenant_id, asignacion_id, materia_id)` para umbral.
2. Sin datos a migrar (tablas nuevas).
3. Rollback: `downgrade()` dropea ambas tablas.

## Open Questions

*(ninguna — el modelo de dominio E7/E8 y RN-01/02/03/04 cierran todas las decisiones de diseño relevantes)*
