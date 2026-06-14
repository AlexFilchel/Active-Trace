## Context

C-07 entregó `Usuario`, `Asignacion` (con `desde`/`hasta` y `estado_vigencia` derivado), `Materia`, `Carrera`, `Cohorte` y el RBAC con permisos seedeados. Este change agrega la Épica 6: encuentros sincrónicos y guardias. Introduce tres tablas nuevas (`slot_encuentro`, `instancia_encuentro`, `guardia`) y la lógica de generación de instancias recurrentes.

El dominio de governance es **MEDIO**: se implementa con checkpoints y se surfacean las decisiones no obvias. No toca auth, RBAC, multi-tenancy ni liquidaciones (dominios críticos).

Modelo de dominio (KB §E9–E11):
- **SlotEncuentro**: plantilla de recurrencia (asignacion_id, materia_id, titulo, hora, dia_semana, fecha_inicio, cant_semanas, fecha_unica nullable, meet_url, vig_desde, vig_hasta).
- **InstanciaEncuentro**: encuentro concreto (slot_id nullable, materia_id, fecha, hora, titulo, estado, meet_url, video_url nullable, comentario). Un slot 1→N instancias.
- **Guardia**: registro de atención (asignacion_id, materia_id, carrera_id, cohorte_id, dia, horario, estado, comentarios, creada_at).

## Goals / Non-Goals

**Goals:**
- Exponer `/api/encuentros/*` y `/api/guardias/*` con permisos fail-closed.
- Crear encuentro recurrente que genera exactamente `cant_semanas` instancias semanales desde `fecha_inicio` (RN-13).
- Crear encuentro único (sin recurrencia, una sola instancia).
- Editar una instancia: `estado`, `meet_url`, `video_url`, `comentario`.
- Generar bloque HTML con el calendario de encuentros y grabaciones (F6.4).
- Vista admin global de encuentros del tenant (F6.5).
- Registro de guardia por el tutor, consulta filtrada global y exportación CSV (F6.6).
- Auditar operaciones que crean/modifican encuentros y guardias.

**Non-Goals:**
- Frontend (otra fase).
- Integración automática que publique el bloque HTML en Moodle: el sistema **genera** el bloque; embeberlo es una acción manual del docente (FL-06 paso 8).
- Notificaciones/recordatorios automáticos de encuentros.
- Edición de un slot completo con re-generación de instancias (solo se editan instancias individuales en F6.3).

## Decisions

### 1. La generación de instancias recurrentes es lógica de Service, no de Repository

`EncuentroService.crear_recurrente` ejecuta en una sola transacción:
1. Crea el `SlotEncuentro` con `cant_semanas = N`.
2. Genera N `InstanciaEncuentro` en estado `Programado`, una por semana: `fecha_inicio + 7*k` para `k` en `0..N-1`, copiando `hora`, `titulo` y `meet_url` del slot.
3. Commit atómico.

La fecha de cada instancia se calcula con `timedelta(weeks=k)` sobre `fecha_inicio` (que ya cae en el `dia_semana` indicado — el frontend/cliente provee una `fecha_inicio` coherente con el día; el backend no reajusta al día de la semana para evitar ambigüedad). **Alternativa descartada**: bucle de inserts en el router — viola "no lógica en routers".

### 2. Encuentro único = slot con `cant_semanas = 0` y `fecha_unica`

`EncuentroService.crear_unico` crea un `SlotEncuentro` con `cant_semanas = 0`, `fecha_unica` seteada, `fecha_inicio = fecha_unica`, y exactamente **una** `InstanciaEncuentro` en esa fecha. Mantener el slot incluso para el caso único unifica el modelo: toda instancia tiene un slot padre y la vista admin no necesita ramas especiales. **Alternativa descartada**: `InstanciaEncuentro` con `slot_id = NULL` para el caso único — el modelo lo permite (slot_id es nullable) pero genera dos caminos de creación divergentes; preferimos un solo camino.

### 3. Edición de instancia solo toca los 4 campos de F6.3

`PATCH /api/encuentros/instancias/{id}` acepta únicamente `estado`, `meet_url`, `video_url`, `comentario` (todos opcionales; schema `extra='forbid'`). No se permite mover la fecha/hora ni cambiar la materia desde acá. Transiciones de `estado` válidas: `Programado → Realizado`, `Programado → Cancelado`, `Realizado → Realizado` (re-edición de comentario/video). `video_url` solo tiene sentido cuando el estado es o pasa a `Realizado`, pero no se valida estrictamente (se permite cargarlo anticipadamente).

### 4. Bloque HTML se genera server-side y se devuelve como texto

`GET /api/encuentros/bloque-html?materia_id=&cohorte_id=` devuelve un string HTML (`{"html": "<table>…"}`) con las instancias ordenadas por fecha: título, fecha, hora, link de `meet_url` y, si existe, link de `video_url`. Generación síncrona (volumen acotado por materia). El sistema **no** publica en el LMS; solo entrega el fragmento. **Alternativa descartada**: plantilla Jinja2 — para una tabla simple, f-strings con escapado (`html.escape`) son suficientes y evitan una dependencia de templating en una capa de servicio.

### 5. Permisos: alineación con el seed real de `003_rbac.py`

El catálogo seedeado tiene `encuentros:gestionar` y `guardias:registrar`; **no existe** `encuentros:ver` ni `guardias:ver`. Decisión:
- Todos los endpoints de `/api/encuentros/*` (incluida la vista admin F6.5 y el bloque HTML) requieren `encuentros:gestionar`. Lo tienen TUTOR, PROFESOR, COORDINADOR, NEXO y ADMIN — cubre tanto a quien crea como a quien supervisa.
- Todos los endpoints de `/api/guardias/*` requieren `guardias:registrar`. Lo tienen TUTOR, PROFESOR, COORDINADOR y ADMIN — cubre tanto el alta del tutor como la consulta/export de coordinación.

No se crean permisos nuevos ni se modifica el seed RBAC (dominio CRÍTICO). Si en el futuro se quiere distinguir "ver" de "gestionar", se agrega en un change de RBAC dedicado.

### 6. La vista admin global NO filtra por asignación del usuario

`GET /api/encuentros` (listado admin) devuelve todas las instancias del tenant (scope de tenant obligatorio), sin restringir al docente que las creó. El filtro de tenant lo aplica `TenantScopedRepository` por defecto. Filtros opcionales por `materia_id`, `cohorte_id`, `estado`, rango de fechas.

### 7. Exportación de guardias síncrona en CSV

`GET /api/guardias/exportar` genera un CSV en el request (mismo patrón que C-08 `exportar_equipo`): docente (usuario_id), materia, carrera, cohorte, dia, horario, estado, comentarios. Volumen acotado; si crece, se mueve al worker sin cambiar el contrato.

### 8. Identidad y tenant siempre desde la sesión

`asignacion_id` / `actor_id` y `tenant_id` se resuelven desde el `AuthenticatedUser` (JWT verificado). El cliente nunca provee `tenant_id` ni puede registrar una guardia "a nombre de" otro: el `asignacion_id` enviado se valida contra el tenant del usuario autenticado.

## Risks / Trade-offs

- **[Riesgo] `fecha_inicio` no coincide con `dia_semana`** → Se acepta `fecha_inicio` tal cual y se generan instancias a +7 días. Mitigation: el schema valida que `dia_semana` y `fecha_inicio.weekday()` coincidan (422 si no), evitando series desalineadas.
- **[Riesgo] `cant_semanas` muy grande infla la tabla** → Mitigation: el schema acota `cant_semanas` a un máximo razonable (p.ej. 1..52). Encuentro único usa `cant_semanas = 0`.
- **[Trade-off] Un solo permiso (`encuentros:gestionar`) para crear y ver** → Simple y alineado al seed actual; pierde granularidad ver/gestionar. Aceptable: la matriz de la KB ya da el permiso a todos los roles relevantes.
- **[Trade-off] Bloque HTML como string** → Simple y suficiente para una tabla; si en el futuro se necesita estilado complejo se migra a plantilla sin cambiar el contrato del endpoint.
- **[Riesgo] Borrado de slot deja instancias huérfanas** → Mitigation: FK `instancia_encuentro.slot_id` con `ondelete="SET NULL"` (instancias independientes) o soft-delete del slot sin tocar instancias; este change usa soft-delete (regla dura) y no expone borrado de slot en la API.
