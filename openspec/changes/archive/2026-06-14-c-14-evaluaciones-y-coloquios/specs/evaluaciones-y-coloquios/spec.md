## ADDED Requirements

### Requirement: Crear convocatoria de coloquio con días y cupos
El sistema SHALL permitir crear una `Evaluacion` de tipo `Coloquio` definiendo materia, cohorte, instancia, y un conjunto de días disponibles con su cupo por día. La operación crea un `DiaEvaluacion` por cada día indicado, en una transacción atómica, dentro del tenant del usuario autenticado. Requiere permiso `coloquios:gestionar`.

#### Scenario: Crear convocatoria genera los días reservables con cupo
- **WHEN** un COORDINADOR envía `POST /api/coloquios` con `materia_id`, `cohorte_id`, `instancia = "Coloquio Final"` y `dias = [{fecha, cupo_total: 10}, {fecha, cupo_total: 5}]`
- **THEN** el sistema crea una `Evaluacion` en estado `Abierta` y exactamente 2 `DiaEvaluacion` con sus cupos, dentro del tenant del usuario autenticado

#### Scenario: Cupo no positivo es rechazado
- **WHEN** se envía un día con `cupo_total` menor o igual a 0
- **THEN** el sistema responde 422 sin crear la convocatoria ni los días

#### Scenario: Campo no permitido es rechazado
- **WHEN** el payload incluye un campo fuera del schema declarado
- **THEN** el sistema responde 422 (schema `extra='forbid'`)

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin permiso `coloquios:gestionar` intenta crear una convocatoria
- **THEN** el sistema responde 403 y no crea ningún registro

---

### Requirement: Importar alumnos a una convocatoria
El sistema SHALL permitir cargar o actualizar el conjunto de alumnos candidatos habilitados de una convocatoria, creando un `CandidatoEvaluacion` por alumno. La operación es idempotente: reimportar no duplica candidatos. Requiere permiso `coloquios:gestionar`.

#### Scenario: Importar candidatos los habilita para reservar
- **WHEN** un COORDINADOR envía `POST /api/coloquios/{id}/candidatos` con una lista de `alumno_id`
- **THEN** el sistema registra un `CandidatoEvaluacion` por alumno dentro del tenant, y esos alumnos quedan habilitados para reservar turno

#### Scenario: Reimportar no duplica
- **WHEN** se importa un `alumno_id` que ya es candidato de la convocatoria
- **THEN** el sistema no crea un registro duplicado y la operación responde 200

#### Scenario: Convocatoria de otro tenant es rechazada
- **WHEN** se importan candidatos a una `evaluacion_id` que no pertenece al tenant del usuario autenticado
- **THEN** el sistema responde 404 y no crea candidatos

---

### Requirement: Reserva de turno por el alumno con control de cupo
El sistema SHALL permitir que un ALUMNO candidato reserve un turno en un `DiaEvaluacion` con cupo disponible. La reserva crea una `ReservaEvaluacion` en estado `Activa` y descuenta cupo (derivado del conteo de reservas activas). La identidad del alumno se toma SIEMPRE de la sesión. Requiere permiso `evaluacion:reservar_instancia`.

#### Scenario: Reserva con cupo disponible descuenta cupo
- **WHEN** un ALUMNO candidato envía `POST /api/coloquios/{id}/reservas` con `dia_evaluacion_id` de un día con cupo libre
- **THEN** el sistema crea una `ReservaEvaluacion` en estado `Activa` para el alumno de la sesión, y el cupo libre de ese día disminuye en 1

#### Scenario: Sin cupo se rechaza
- **WHEN** un ALUMNO intenta reservar un `DiaEvaluacion` cuyas reservas activas ya igualan `cupo_total`
- **THEN** el sistema responde 409 y no crea la reserva

#### Scenario: Alumno no candidato es rechazado
- **WHEN** un ALUMNO que no es `CandidatoEvaluacion` de la convocatoria intenta reservar
- **THEN** el sistema responde 403 y no crea la reserva

#### Scenario: Reserva duplicada del mismo alumno es rechazada
- **WHEN** un ALUMNO con una reserva `Activa` en la convocatoria intenta reservar otro turno de la misma convocatoria
- **THEN** el sistema responde 409 y no crea una segunda reserva

#### Scenario: Identidad desde sesión
- **WHEN** el payload de reserva incluye un `alumno_id` distinto al de la sesión
- **THEN** el sistema ignora el dato del payload y usa el alumno autenticado (o responde 422 si el schema lo prohíbe)

---

### Requirement: Cancelar reserva libera cupo
El sistema SHALL permitir que un ALUMNO cancele su propia `ReservaEvaluacion`, pasándola a estado `Cancelada`, lo que libera el cupo del día. Requiere permiso `evaluacion:reservar_instancia`.

#### Scenario: Cancelar libera el cupo
- **WHEN** un ALUMNO cancela su reserva activa mediante `PATCH /api/coloquios/reservas/{id}` con `estado = Cancelada`
- **THEN** la reserva queda en estado `Cancelada` y el cupo libre del día aumenta en 1, permitiendo reservar de nuevo

#### Scenario: No se puede cancelar la reserva de otro alumno
- **WHEN** un ALUMNO intenta cancelar una reserva que no le pertenece
- **THEN** el sistema responde 404 y no modifica la reserva

---

### Requirement: Listado de convocatorias con métricas operativas
El sistema SHALL exponer un listado de convocatorias del tenant con sus métricas operativas derivadas: materia, instancia, días disponibles, convocados, reservas activas y cupos libres. Requiere permiso `coloquios:gestionar`.

#### Scenario: Listado muestra métricas derivadas
- **WHEN** un COORDINADOR realiza `GET /api/coloquios`
- **THEN** el sistema devuelve cada convocatoria del tenant con `convocados` (count de candidatos), `reservas_activas` (count de reservas Activa) y `cupos_libres` (suma de cupos menos reservas activas)

#### Scenario: Tenant aislado
- **WHEN** dos usuarios de distintos tenants listan convocatorias
- **THEN** cada uno ve únicamente las convocatorias de su propio tenant

---

### Requirement: Panel de métricas de coloquios
El sistema SHALL exponer un panel agregado con: total de alumnos convocados, cantidad de convocatorias/instancias activas, total de reservas activas y total de notas registradas, derivados de los datos del tenant. Requiere permiso `coloquios:gestionar`.

#### Scenario: Panel agrega las métricas del tenant
- **WHEN** un COORDINADOR realiza `GET /api/coloquios/metricas`
- **THEN** el sistema devuelve `convocados`, `instancias_activas`, `reservas_activas` y `notas_registradas` calculados sobre las convocatorias del tenant

---

### Requirement: Registro consolidado de resultados de coloquio
El sistema SHALL permitir registrar o actualizar la `nota_final` de un alumno en una convocatoria (`ResultadoEvaluacion`) y consultar el registro académico consolidado de resultados por convocatoria. Requiere permiso `coloquios:gestionar`.

#### Scenario: Registrar resultado consolidado
- **WHEN** un COORDINADOR envía `POST /api/coloquios/{id}/resultados` con `alumno_id` y `nota_final`
- **THEN** el sistema crea un `ResultadoEvaluacion` para ese alumno en la convocatoria, dentro del tenant

#### Scenario: Actualizar resultado existente no duplica
- **WHEN** se registra un resultado para un `alumno_id` que ya tiene `ResultadoEvaluacion` en la convocatoria
- **THEN** el sistema actualiza la `nota_final` existente sin crear un registro duplicado

#### Scenario: Consultar resultados consolidados
- **WHEN** un COORDINADOR realiza `GET /api/coloquios/{id}/resultados`
- **THEN** el sistema devuelve la lista de resultados (alumno, nota_final) de esa convocatoria dentro del tenant

---

### Requirement: Administración global de coloquios
El sistema SHALL permitir la edición y el cierre de convocatorias, y exponer la agenda consolidada de reservas activas por convocatoria. Una convocatoria `Cerrada` no admite nuevas reservas. Requiere permiso `coloquios:gestionar`.

#### Scenario: Cerrar convocatoria impide nuevas reservas
- **WHEN** un COORDINADOR cierra una convocatoria mediante `PATCH /api/coloquios/{id}` con `estado = Cerrada` y luego un ALUMNO intenta reservar en ella
- **THEN** la convocatoria queda en estado `Cerrada` y la reserva posterior responde 409

#### Scenario: Agenda de reservas activas
- **WHEN** un COORDINADOR realiza `GET /api/coloquios/{id}/agenda`
- **THEN** el sistema devuelve las reservas en estado `Activa` de esa convocatoria, agrupadas por día, dentro del tenant

---

### Requirement: Auditoría de operaciones de coloquios
El sistema SHALL registrar una entrada en `AuditLog` para las operaciones que crean, editan o cierran convocatorias, y para las reservas y cancelaciones de turno.

#### Scenario: Crear convocatoria registra auditoría
- **WHEN** se completa la creación de una convocatoria
- **THEN** existe un `AuditLog` con `accion = COLOQUIO_CREAR`, el `actor` del request y `filas_afectadas` igual al número de días creados

#### Scenario: Reservar turno registra auditoría
- **WHEN** un ALUMNO completa una reserva de turno
- **THEN** existe un `AuditLog` con `accion = COLOQUIO_RESERVAR` y el `actor` del request
