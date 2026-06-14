# Design: C-14 Evaluaciones y Coloquios

## Context

Implementa el dominio E14 (Evaluación) para soportar la Épica 7 (Coloquios) y el flujo FL-07. El stack y las reglas duras son las del proyecto: FastAPI async, SQLAlchemy 2.0 async, Alembic, PostgreSQL, Pydantic v2 (`extra='forbid'`), JWT con identidad siempre desde sesión, multi-tenancy row-level, RBAC fail-closed, soft delete, auditoría obligatoria, flujo unidireccional Routers → Services → Repositories → Models.

Governance MEDIO: el control de cupo es la regla de negocio crítica; se implementa con locking a nivel de fila para evitar sobre-reserva en concurrencia.

## Goals / Non-Goals

**Goals**
- Modelos `Evaluacion`, `ReservaEvaluacion`, `ResultadoEvaluacion` (E14) con `tenant_id` y soft delete.
- Crear convocatoria con días y cupos; reservar turno descontando cupo; rechazar sin cupo; cancelar liberando cupo.
- Importar/actualizar padrón de candidatos a una convocatoria.
- Métricas (convocados / reservas activas / cupos libres / notas) y listado de convocatorias.
- Registro consolidado de resultados.
- Permiso nuevo `coloquios:gestionar` para COORDINADOR/ADMIN; reserva con `evaluacion:reservar_instancia` (ALUMNO).

**Non-Goals**
- Frontend (cubierto por changes de la Fase 6 / `C-21`+).
- Integración con Moodle WS para coloquios.
- Notificaciones por email de la reserva (se delega a Comunicación, C-12).
- Calendarización académica general (E15 `FechaAcademica`) — no es parte de este change.

## Decisions

### D1 — Modelo de cupos: tabla de días, no JSONB

El KB modela `Evaluacion.dias_disponibles` como un entero (ventana en días). Pero F7.3/FL-07 requieren **días concretos con cupo por día** y reservas que apuntan a un día específico. Para representar esto sin denormalizar contadores (regla del KB: contadores derivados, no almacenados), se introduce una tabla hija `dia_evaluacion`:

- `Evaluacion` — la convocatoria (materia, cohorte, tipo, instancia, dias_disponibles como metadato de ventana, estado Abierta/Cerrada).
- `DiaEvaluacion` — un día reservable de la convocatoria (`fecha`, `cupo_total`). El cupo libre se **deriva** contando `ReservaEvaluacion` activas de ese día; no se guarda un contador.
- `ReservaEvaluacion` — apunta a `evaluacion_id` y `dia_evaluacion_id`, con `alumno_id`, `fecha_hora`, `estado` (Activa | Cancelada).

**Tradeoff**: agrega una entidad respecto del KB literal, pero es la forma correcta de modelar "cupos por día" sin contadores denormalizados. Se documenta como extensión coherente con FL-07. Alternativa descartada: JSONB con `{fecha: cupo}` — rompería la atomicidad del control de cupo y la trazabilidad de reservas por día.

### D2 — Control de cupo bajo concurrencia (SELECT ... FOR UPDATE)

Reservar un turno es la operación crítica. Para evitar sobre-reserva con dos alumnos compitiendo por el último cupo:

1. `SELECT` del `DiaEvaluacion` con `with_for_update()` (lock de fila) dentro de la transacción.
2. Contar reservas Activas de ese día.
3. Si `reservas_activas >= cupo_total` → `SinCupoError` (409), rollback.
4. Si hay cupo → crear `ReservaEvaluacion` Activa → audit → commit (libera el lock).

Una reserva por alumno por convocatoria: constraint único parcial `(tenant_id, evaluacion_id, alumno_id)` sobre reservas no canceladas. Si el alumno ya tiene reserva Activa → `ReservaDuplicadaError` (409).

### D3 — Permiso nuevo `coloquios:gestionar`

El seed RBAC (003) solo tiene `evaluacion:reservar_instancia` (ALUMNO). No existe permiso de gestión de coloquios. Siguiendo el patrón de la migración 009 (que agregó `comunicacion:aprobar`), la migración 011 inserta el permiso `coloquios:gestionar` por tenant y lo asigna a COORDINADOR y ADMIN (idempotente, `ON CONFLICT DO NOTHING`). La reserva del alumno reutiliza `evaluacion:reservar_instancia`.

### D4 — Importar candidatos: tabla de candidatos por convocatoria

F7.2 importa el padrón de alumnos **habilitados** para la convocatoria. Se modela como `CandidatoEvaluacion` (`evaluacion_id`, `alumno_id`). La reserva de un alumno valida que sea candidato de esa convocatoria (fail-closed: no candidato → 403/422). "Convocados" en las métricas = count de candidatos.

> Nota de alcance: para mantener el change acotado y alineado al KB literal (que nombra solo 3 entidades), `CandidatoEvaluacion` y `DiaEvaluacion` son entidades de soporte derivadas de los requisitos de F7.2/F7.3. Se documentan aquí como decisión explícita. Si la coordinación del proyecto prefiere no introducirlas, ver "Open Questions".

### D5 — Resultado consolidado

`ResultadoEvaluacion` (`evaluacion_id`, `alumno_id`, `nota_final` texto — numérica o cualitativa). Registro/actualización bajo `coloquios:gestionar`. El registro académico consolidado (F7.5) es un listado de resultados por convocatoria.

### D6 — Índices (evitar el bug de tenant_id duplicado)

`TenantScopedMixin` ya crea `ix_<tabla>_tenant_id`. **No** redeclarar ese índice en `__table_args__`. Solo se indexan columnas adicionales: `materia_id` y `cohorte_id` en `evaluacion`; `evaluacion_id` y `dia_evaluacion_id` en `reserva_evaluacion`; `evaluacion_id` en `resultado_evaluacion`, `dia_evaluacion` y `candidato_evaluacion`. Las FK con `index=True` inline (p.ej. `alumno_id`) se autoindexan; el resto se declaran en `__table_args__`.

## Risks / Trade-offs

- **Concurrencia de cupo**: mitigado con `with_for_update()`. Riesgo residual si se escala a múltiples réplicas con réplicas de lectura — el lock va contra la primaria, OK.
- **Desvío del KB literal**: se introducen `DiaEvaluacion` y `CandidatoEvaluacion` (no nombradas en E14). Mitigación: documentadas como soporte de F7.2/F7.3; abiertas a revisión de coordinación.
- **Soft delete + unicidad de reserva**: el constraint de "una reserva activa por alumno" debe ser parcial (`WHERE deleted_at IS NULL AND estado = 'Activa'`) para no bloquear re-reservas tras cancelar.

## Migration Plan

- Migración `011_evaluaciones_coloquios` (revision `011_evaluaciones_coloquios`, down_revision `010_encuentros_guardias`).
- Crea `evaluacion`, `dia_evaluacion`, `candidato_evaluacion`, `reserva_evaluacion`, `resultado_evaluacion`.
- FKs: `dia_evaluacion.evaluacion_id` → `evaluacion.id` (CASCADE); `reserva_evaluacion.evaluacion_id`/`dia_evaluacion_id` → respectivas (RESTRICT); `*.alumno_id` → `usuario.id` (RESTRICT); `*.materia_id`/`cohorte_id` → `materia.id`/`cohorte.id` (RESTRICT).
- Índice único parcial sobre reservas activas por `(tenant_id, evaluacion_id, alumno_id)`.
- Seed idempotente del permiso `coloquios:gestionar` para COORDINADOR/ADMIN por tenant.
- `downgrade()` elimina tablas en orden inverso de FK y borra el permiso/asignaciones agregadas.

## Open Questions

- **OQ-1**: ¿La coordinación acepta `DiaEvaluacion` + `CandidatoEvaluacion` como entidades de soporte, o prefiere modelar cupos en JSONB sobre `Evaluacion`? (Decisión actual: tablas; ver D1/D4). No bloquea — es extensión coherente con FL-07.
