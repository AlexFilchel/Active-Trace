# calificaciones Specification

## Purpose
TBD - created by archiving change c-10-calificaciones-y-umbral. Update Purpose after archive.
## Requirements
### Requirement: Importar calificaciones desde archivo LMS — vista previa

El sistema SHALL procesar un archivo exportado del LMS y devolver la lista de actividades detectadas para que el usuario seleccione cuáles incluir antes de confirmar la importación.

- Las columnas que terminan en `(Real)` se clasifican como actividad de nota numérica (RN-01).
- Las columnas cuyos valores pertenecen al conjunto configurable `{Satisfactorio, Supera lo esperado, No satisfactorio, No alcanzado}` se clasifican como actividad de nota textual (RN-02).
- Una columna no puede ser simultáneamente numérica y textual; la clasificación es mutuamente excluyente.
- La vista previa no persiste ningún dato; es un análisis en memoria del archivo recibido.
- El endpoint requiere permiso `calificaciones:importar`.

#### Scenario: Archivo con columnas numéricas y textuales detectadas correctamente
WHEN se sube un archivo xlsx con columnas `"Tarea 1 (Real)"`, `"Quiz (Real)"` y `"Trabajo Final"` (con valores textuales)
THEN la respuesta incluye `actividades_numericas: ["Tarea 1", "Quiz"]` y `actividades_textuales: ["Trabajo Final"]`

#### Scenario: Archivo sin columnas de actividad válidas retorna lista vacía
WHEN se sube un archivo xlsx cuyas columnas no contienen actividades evaluables reconocibles
THEN la respuesta retorna `actividades_numericas: []` y `actividades_textuales: []` con status 200

#### Scenario: Sin permiso retorna 403
WHEN el usuario autenticado no tiene el permiso `calificaciones:importar`
THEN el endpoint retorna HTTP 403

---

### Requirement: Importar calificaciones — confirmación

El sistema SHALL persistir las calificaciones de los alumnos para las actividades seleccionadas por el usuario, derivando el campo `aprobado` en el momento de inserción.

- Solo se importan actividades explícitamente seleccionadas por el usuario (pasadas en el body de la confirmación).
- Para cada alumno y actividad, se crea un registro `Calificacion` con `origen = Importado`.
- `aprobado` se deriva: si hay `nota_numerica`, se compara con el `umbral_pct` configurado para esa asignación (defecto 60 %); si solo hay `nota_textual`, se evalúa contra los `valores_aprobatorios` del umbral.
- La operación es **scope-isolated**: solo afecta las calificaciones del usuario (actor_id) en esa materia. No modifica datos de otros docentes (RN-04).
- Si ya existían calificaciones del mismo actor para esa materia, se reemplazan (upsert por `entrada_padron_id + actividad`).
- Se registra audit `CALIFICACIONES_IMPORTAR` con conteo de filas afectadas.
- El endpoint requiere permiso `calificaciones:importar`.

#### Scenario: Importación exitosa con actividades seleccionadas
WHEN el usuario confirma importación con actividades `["Tarea 1", "Quiz"]` para una materia con 3 alumnos en el padrón
THEN se crean 6 registros `Calificacion` (2 actividades × 3 alumnos), se retorna HTTP 201 con `calificaciones_importadas: 6` y se registra audit `CALIFICACIONES_IMPORTAR`

#### Scenario: Campo aprobado derivado correctamente para nota numérica
WHEN se importa `nota_numerica = 75` con `umbral_pct = 60` (escala 100)
THEN `aprobado = true`

#### Scenario: Campo aprobado derivado correctamente para nota textual aprobatoria
WHEN se importa `nota_textual = "Satisfactorio"` y `"Satisfactorio"` ∈ `valores_aprobatorios`
THEN `aprobado = true`

#### Scenario: Campo aprobado false para nota textual no aprobatoria
WHEN se importa `nota_textual = "No satisfactorio"` y ese valor no ∈ `valores_aprobatorios`
THEN `aprobado = false`

#### Scenario: Tenant isolation — importación no cruza tenants
WHEN el actor pertenece al tenant A e importa calificaciones para materia del tenant A
THEN ningún registro del tenant B se crea ni modifica

---

### Requirement: Importar reporte de finalización de actividades

El sistema SHALL procesar un archivo de reporte de finalización del LMS para identificar actividades textuales entregadas pero sin calificación (posibles TPs sin corregir).

- Solo aplica a actividades de escala textual (RN-08).
- El cruce es: alumno tiene `finalizado = true` en el reporte Y no tiene `Calificacion` registrada para esa actividad textual.
- No persiste datos; devuelve lista de pares `(alumno, actividad)`.
- El endpoint requiere permiso `calificaciones:importar`.

#### Scenario: Reporte detecta entregas sin calificación textual
WHEN se sube reporte de finalización con alumno A que finalizó "Trabajo Final" pero no tiene calificación textual registrada para esa actividad
THEN la respuesta incluye `{entrada_padron_id: A, actividad: "Trabajo Final"}` en `sin_calificar`

#### Scenario: Actividades numéricas excluidas del reporte
WHEN el reporte incluye finalización de "Tarea 1 (Real)" (actividad numérica)
THEN "Tarea 1 (Real)" no aparece en `sin_calificar` independientemente de si hay calificación

---

### Requirement: Configurar umbral de aprobación por asignación

El sistema SHALL permitir a un docente configurar el umbral de aprobación y los valores aprobatorios textuales para una materia en su asignación.

- El umbral aplica exclusivamente a la asignación del docente activo. No afecta a otros docentes en la misma materia (RN-04).
- Si no existe configuración, el sistema usa `umbral_pct = 60` y `valores_aprobatorios = ["Satisfactorio", "Supera lo esperado"]` como defecto (RN-03).
- `PUT /api/calificaciones/umbral` crea o actualiza `UmbralMateria` para el par `(asignacion_id, materia_id)`.
- `GET /api/calificaciones/umbral` retorna el umbral vigente (explícito o defecto).
- El endpoint requiere permiso `calificaciones:importar`.

#### Scenario: Configuración de umbral persistida correctamente
WHEN el docente hace PUT con `umbral_pct = 70` y `valores_aprobatorios = ["Satisfactorio", "Supera lo esperado"]`
THEN se persiste `UmbralMateria` con esos valores y se retorna HTTP 200

#### Scenario: GET retorna defecto cuando no hay configuración explícita
WHEN no existe `UmbralMateria` para la asignación del docente en esa materia
THEN GET retorna `{umbral_pct: 60, valores_aprobatorios: ["Satisfactorio", "Supera lo esperado"], es_defecto: true}`

#### Scenario: Umbral de un docente no afecta a otro
WHEN el docente A configura `umbral_pct = 80` para la materia M
THEN el docente B que también tiene asignación en M sigue viendo su propio umbral (o el defecto si no configuró)

---

### Requirement: Vaciar calificaciones scope-isolated

El sistema SHALL eliminar (soft-delete o purga) todas las calificaciones del actor en una materia, sin afectar datos de otros docentes.

- La operación elimina únicamente registros `Calificacion` donde `actor_id == usuario_activo` y `materia_id == materia_seleccionada` (RN-04).
- Si no existen calificaciones para ese scope, retorna 200 con `eliminadas: 0`.
- Se registra audit `CALIFICACIONES_IMPORTAR` con detalle `operacion: "vaciado"`.
- El endpoint requiere permiso `calificaciones:importar`.

#### Scenario: Vaciado elimina solo calificaciones del actor
WHEN el docente A ejecuta DELETE en materia M con 5 calificaciones propias y 3 de docente B
THEN se eliminan 5 registros del docente A, los 3 del docente B permanecen intactos, response retorna `eliminadas: 5`

#### Scenario: Vaciado sin calificaciones retorna 200 con cero
WHEN el actor no tiene calificaciones en la materia seleccionada
THEN retorna HTTP 200 con `eliminadas: 0`

