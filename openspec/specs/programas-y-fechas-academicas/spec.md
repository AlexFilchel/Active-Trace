# Spec: programas-y-fechas-academicas

## ADDED Requirements

### Requirement: Registrar programa de materia
El sistema SHALL permitir a COORDINADOR y ADMIN registrar el programa oficial de una materia para una combinación específica de materia × carrera × cohorte, con un título y una referencia de archivo opaca (URL/path al almacenamiento externo). Se registra auditoría `PROGRAMA_CREAR`.

#### Scenario: Crear programa válido
- **WHEN** un COORDINADOR envía `POST /api/programas` con `materia_id`, `carrera_id`, `cohorte_id`, `titulo` y `referencia_archivo`
- **THEN** el sistema crea el programa y retorna 201 con todos los campos incluyendo `cargado_at`

#### Scenario: Sin permiso estructura:gestionar
- **WHEN** un usuario sin permiso `estructura:gestionar` intenta crear un programa
- **THEN** el sistema retorna 403

#### Scenario: Campo obligatorio ausente
- **WHEN** se omite `titulo` o `referencia_archivo`
- **THEN** el sistema retorna 422

#### Scenario: Campo extra en body
- **WHEN** el body incluye un campo no declarado
- **THEN** el sistema retorna 422 (`extra_forbidden`)

---

### Requirement: Listar programas de materia
El sistema SHALL exponer `GET /api/programas` con filtros opcionales por `materia_id`, `carrera_id` y `cohorte_id`. Retorna solo programas del tenant del actor.

#### Scenario: Listar todos los programas del tenant
- **WHEN** un COORDINADOR llama `GET /api/programas`
- **THEN** el sistema retorna todos los programas del tenant

#### Scenario: Filtrar por materia y cohorte
- **WHEN** se pasan `materia_id` y `cohorte_id`
- **THEN** el sistema retorna solo programas que coincidan con ambos filtros (AND)

#### Scenario: Aislamiento de tenant
- **WHEN** un COORDINADOR del tenant A consulta `GET /api/programas`
- **THEN** el sistema NO retorna programas de otro tenant

---

### Requirement: Registrar fecha académica
El sistema SHALL permitir a COORDINADOR y ADMIN registrar fechas de instancias evaluativas (Parcial, TP, Coloquio, Recuperatorio) por materia × cohorte × número de instancia y período. Se registra auditoría `FECHA_ACAT_CREAR`.

#### Scenario: Crear fecha académica válida
- **WHEN** un COORDINADOR envía `POST /api/fechas-academicas` con `materia_id`, `cohorte_id`, `tipo`, `numero`, `periodo`, `fecha` y `titulo`
- **THEN** el sistema crea la fecha y retorna 201

#### Scenario: Tipo inválido
- **WHEN** se envía un `tipo` distinto de `Parcial`, `TP`, `Coloquio`, `Recuperatorio`
- **THEN** el sistema retorna 422

#### Scenario: Número de instancia no positivo
- **WHEN** se envía `numero` ≤ 0
- **THEN** el sistema retorna 422

---

### Requirement: Editar fecha académica
El sistema SHALL permitir editar los campos de una fecha académica existente. Se registra auditoría `FECHA_ACAT_EDITAR`.

#### Scenario: Editar fecha exitosamente
- **WHEN** un COORDINADOR envía `PATCH /api/fechas-academicas/{id}` con campos a modificar
- **THEN** el sistema actualiza solo los campos enviados y retorna 200

#### Scenario: Fecha de otro tenant
- **WHEN** se intenta editar una fecha de otro tenant
- **THEN** el sistema retorna 404

---

### Requirement: Listar fechas académicas
El sistema SHALL exponer `GET /api/fechas-academicas` con filtros opcionales por `materia_id`, `cohorte_id`, `tipo` y `periodo`. Retorna fechas del tenant en orden cronológico ascendente.

#### Scenario: Listar fechas del tenant
- **WHEN** un COORDINADOR llama `GET /api/fechas-academicas`
- **THEN** el sistema retorna todas las fechas del tenant en orden por `fecha` ASC

#### Scenario: Filtrar por tipo y período
- **WHEN** se pasan `tipo=Parcial` y `periodo=2026-1`
- **THEN** el sistema retorna solo fechas que coincidan con ambos filtros

---

### Requirement: Generar fragmento LMS
El sistema SHALL exponer `GET /api/fechas-academicas/fragmento-lms` que recibe `materia_id`, `cohorte_id` y `periodo` y retorna un bloque de texto formateado listo para publicar en el aula virtual del LMS.

#### Scenario: Generar fragmento con fechas
- **WHEN** un COORDINADOR llama con `materia_id`, `cohorte_id` y `periodo` válidos
- **THEN** el sistema retorna un objeto `{ "texto": "..." }` con las fechas formateadas por tipo e instancia

#### Scenario: Sin fechas para el período
- **WHEN** no hay fechas registradas para la combinación dada
- **THEN** el sistema retorna `{ "texto": "" }` con 200

---

### Requirement: Auditoría de programas y fechas
El sistema SHALL registrar entradas de `AuditLog` para `PROGRAMA_CREAR`, `FECHA_ACAT_CREAR` y `FECHA_ACAT_EDITAR`, incluyendo el `id` del recurso afectado en `detalle`.

#### Scenario: Audit al crear programa
- **WHEN** se crea un programa exitosamente
- **THEN** existe un `AuditLog` con `accion=PROGRAMA_CREAR` y `programa_id` en detalle

#### Scenario: Audit al crear fecha
- **WHEN** se crea una fecha académica
- **THEN** existe un `AuditLog` con `accion=FECHA_ACAT_CREAR` y `fecha_academica_id` en detalle
