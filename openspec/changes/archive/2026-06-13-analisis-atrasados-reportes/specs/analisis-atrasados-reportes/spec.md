# analisis-atrasados-reportes Specification

## ADDED Requirements

### Requirement: Consultar alumnos atrasados

El sistema SHALL exponer una consulta de alumnos atrasados basada en calificaciones, padrón activo y umbral vigente de la materia, protegida por el permiso `atrasados:ver`.

- Un alumno atrasado MUST incluir al menos un motivo: `actividad_faltante` o `nota_bajo_umbral`.
- Una actividad faltante MUST entenderse como una actividad del conjunto analizado/importado para la materia sin calificación registrada para el alumno del padrón activo.
- Una nota bajo umbral MUST evaluarse contra el umbral aplicable a la asignación; si no existe configuración explícita, MUST usarse el defecto definido por `calificaciones`.
- La consulta MUST filtrar por `tenant_id` y alcance autorizado desde la sesión, no desde parámetros de identidad del request.

#### Scenario: Alumno con actividad faltante aparece como atrasado
- **WHEN** un alumno del padrón activo no tiene calificación para una actividad analizada de la materia
- **THEN** la respuesta de atrasados incluye al alumno con motivo `actividad_faltante`

#### Scenario: Alumno con nota inferior al umbral aparece como atrasado
- **WHEN** un alumno tiene `nota_numerica = 50` y el umbral aplicable es `60`
- **THEN** la respuesta de atrasados incluye al alumno con motivo `nota_bajo_umbral`

#### Scenario: Usuario sin permiso no accede a atrasados
- **WHEN** un usuario autenticado sin `atrasados:ver` consulta `/api/analisis/atrasados`
- **THEN** el sistema retorna HTTP 403 sin exponer datos académicos

#### Scenario: Tenant isolation en consulta de atrasados
- **WHEN** un usuario del tenant A consulta atrasados
- **THEN** ningún alumno, calificación ni materia del tenant B aparece en la respuesta

---

### Requirement: Consultar ranking de actividades aprobadas

El sistema SHALL exponer un ranking de alumnos ordenado por cantidad de actividades aprobadas, excluyendo a quienes no tengan ninguna actividad aprobada (RN-09).

- El ranking MUST incluir solo alumnos con `aprobadas_count >= 1`.
- El orden principal MUST ser descendente por `aprobadas_count`.
- Los empates MUST resolverse con un orden estable por apellido/nombre o identificador interno.
- La consulta MUST requerir `atrasados:ver` y aplicar tenant/alcance desde sesión.

#### Scenario: Alumno sin aprobadas queda excluido
- **WHEN** un alumno tiene `aprobadas_count = 0`
- **THEN** el alumno no aparece en el ranking

#### Scenario: Ranking ordena por aprobadas descendente
- **WHEN** el alumno A tiene 3 aprobadas y el alumno B tiene 1 aprobada
- **THEN** A aparece antes que B en la respuesta

---

### Requirement: Consultar reportes rápidos por materia

El sistema SHALL exponer un resumen por materia con métricas clave de actividades, aprobaciones, atrasados y estado de datos.

- El resumen MUST indicar si no hay datos importados o no hay actividades analizadas.
- El resumen MUST incluir conteos de alumnos del padrón activo, actividades analizadas, aprobaciones y atrasados cuando existan datos.
- La consulta MUST requerir `atrasados:ver` y respetar alcance del usuario.

#### Scenario: Materia sin datos importados retorna estado informativo
- **WHEN** la materia consultada no tiene calificaciones importadas para el alcance autorizado
- **THEN** el resumen retorna status 200 con estado informativo de datos ausentes y métricas en cero

#### Scenario: Materia con datos retorna métricas consolidadas
- **WHEN** existen calificaciones para una materia y padrón activo
- **THEN** el resumen incluye conteos de alumnos, actividades, aprobaciones y atrasados

---

### Requirement: Consultar notas finales agrupadas

El sistema SHALL calcular una nota final agrupada por alumno a partir de las actividades incluidas en el análisis de la materia.

- La respuesta MUST agrupar resultados por alumno del padrón activo.
- La respuesta MUST listar actividades consideradas y valores usados en el cálculo.
- Si no existe una fórmula ponderada configurada, el cálculo MUST usar una agregación determinística documentada por el servicio para las actividades numéricas disponibles.
- La consulta MUST requerir `atrasados:ver`.

#### Scenario: Nota final agrupada por alumno
- **WHEN** un alumno tiene calificaciones numéricas en actividades incluidas de una materia
- **THEN** la respuesta contiene una única fila del alumno con actividades consideradas y nota final calculada

#### Scenario: Alumno sin notas numéricas calculables queda marcado sin nota final
- **WHEN** un alumno no tiene calificaciones numéricas disponibles para las actividades incluidas
- **THEN** la respuesta lo marca como sin nota final calculable sin inventar un valor

---

### Requirement: Consultar monitores de seguimiento

El sistema SHALL exponer un monitor filtrable de estado de actividades para seguimiento académico.

- PROFESOR y TUTOR MUST ver solo alumnos dentro de sus asignaciones/alcance autorizado.
- COORDINADOR y ADMIN MAY consultar transversalmente dentro del tenant y MUST poder filtrar por rango de fechas.
- Los filtros MUST incluir materia, regional, comisión, búsqueda libre por alumno, estado de actividad y criterio de clasificación cuando existan esos datos.
- La consulta MUST requerir `atrasados:ver`.

#### Scenario: Profesor ve solo alumnos de su alcance
- **WHEN** un PROFESOR consulta el monitor
- **THEN** la respuesta incluye únicamente alumnos de sus materias/comisiones autorizadas

#### Scenario: Coordinación filtra por rango de fechas
- **WHEN** un COORDINADOR consulta el monitor con `fecha_desde` y `fecha_hasta`
- **THEN** la respuesta incluye solo registros dentro del rango solicitado y del tenant activo

#### Scenario: Filtros combinados reducen resultados
- **WHEN** se aplican filtros de materia, regional, comisión y búsqueda libre
- **THEN** la respuesta contiene solo alumnos que cumplen todos los filtros autorizados

---

### Requirement: Exportar TPs sin corregir

El sistema SHALL permitir exportar trabajos prácticos sin corregir detectados como entregas finalizadas sin calificación textual, aplicando RN-07 y RN-08.

- El export MUST incluir únicamente actividades de escala textual.
- El export MUST excluir actividades numéricas.
- El export MUST generar un archivo descargable con alumno, materia, actividad y datos de seguimiento necesarios.
- El endpoint MUST requerir `atrasados:ver` y aplicar tenant/alcance desde sesión.

#### Scenario: Export incluye entrega textual finalizada sin calificación
- **WHEN** un alumno finalizó una actividad textual y no existe calificación registrada para esa actividad
- **THEN** el export incluye una fila para ese alumno y actividad

#### Scenario: Export excluye actividad numérica sin nota
- **WHEN** una actividad numérica no tiene nota registrada
- **THEN** esa actividad no aparece en el export de TPs sin corregir

#### Scenario: Export sin permiso retorna 403
- **WHEN** un usuario sin `atrasados:ver` solicita el export
- **THEN** el sistema retorna HTTP 403 y no genera archivo
