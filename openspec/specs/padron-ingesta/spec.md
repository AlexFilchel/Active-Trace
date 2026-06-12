# padron-ingesta Specification

## Purpose
TBD - created by archiving change c-09-padron-ingesta-moodle. Update Purpose after archive.
## Requirements
### Requirement: Cargar padrón desde archivo

El sistema SHALL aceptar archivos `.xlsx` y `.csv` en formato de exportación estándar de Moodle para cargar el padrón de alumnos de una materia/cohorte. La carga SHALL detectar columnas por nombre (case-insensitive): `Nombre`, `Apellido(s)`, `Dirección de correo`, `Grupos`. Si alguna columna obligatoria falta, la operación SHALL retornar 422 con la lista de columnas faltantes.

#### Scenario: Carga exitosa crea VersionPadron activa y sus EntradaPadron

- **WHEN** un usuario con `padron:gestionar` hace POST `/api/padron/cargar` con un archivo válido, `materia_id` y `cohorte_id`
- **THEN** el sistema crea una `VersionPadron` con `activa=true` para ese (tenant, materia, cohorte)
- **AND** crea una `EntradaPadron` por cada fila del archivo con nombre, apellidos, email cifrado y comisión
- **AND** retorna 201 con `version_id`, `entradas_cargadas` y `version_anterior_desactivada` (bool)
- **AND** registra acción `PADRON_CARGAR` en `audit_log`

#### Scenario: Columna obligatoria faltante retorna 422

- **WHEN** el archivo subido no contiene la columna `Dirección de correo`
- **THEN** el sistema retorna 422 con `detail` listando las columnas faltantes
- **AND** no crea ninguna versión ni entrada en la base de datos

#### Scenario: Archivo vacío (sin filas de datos) retorna 422

- **WHEN** el archivo contiene solo headers sin filas de datos
- **THEN** el sistema retorna 422 con `detail: "El archivo no contiene alumnos"`

---

### Requirement: Versionado destructivo — una versión activa por contexto

Al cargar un nuevo padrón, el sistema SHALL desactivar la versión anterior (si existe) para el mismo (tenant, materia, cohorte). La versión anterior NO SHALL ser eliminada de la base de datos (preserve historial). Solo una `VersionPadron` SHALL tener `activa=true` por (tenant_id, materia_id, cohorte_id) en cualquier momento.

#### Scenario: Nueva carga desactiva la versión anterior

- **WHEN** ya existe una `VersionPadron` activa para (materia_id, cohorte_id) del tenant
- **AND** se carga un nuevo padrón para el mismo contexto
- **THEN** la versión anterior queda con `activa=false`
- **AND** la nueva versión tiene `activa=true`
- **AND** las entradas de la versión anterior permanecen en la base de datos

#### Scenario: Primera carga no falla por versión previa inexistente

- **WHEN** no existe ninguna versión para ese (materia_id, cohorte_id)
- **AND** se carga el primer padrón
- **THEN** la operación crea la primera versión con `activa=true` sin error

---

### Requirement: Carga desde Moodle Web Services

El sistema SHALL soportar ingesta del padrón usando la API de Moodle (`core_enrol_get_enrolled_users`) para tenants que tengan `moodle_ws_url` y `moodle_ws_token` configurados. Si el tenant no tiene WS configurado, el endpoint de ingesta vía WS SHALL retornar 422 con mensaje explicativo.

#### Scenario: Ingesta exitosa desde Moodle WS

- **WHEN** el tenant tiene `moodle_ws_url` y `moodle_ws_token` configurados
- **AND** se hace POST `/api/padron/cargar-moodle` con `materia_id`, `cohorte_id` y `moodle_course_id`
- **THEN** el sistema llama a Moodle WS, obtiene la lista de usuarios matriculados
- **AND** crea `VersionPadron` + `EntradaPadron` con la misma lógica que la carga por archivo
- **AND** retorna 201 con `version_id` y `entradas_cargadas`

#### Scenario: Tenant sin WS configurado retorna 422

- **WHEN** el tenant no tiene `moodle_ws_url` configurado
- **AND** se intenta POST `/api/padron/cargar-moodle`
- **THEN** el sistema retorna 422 con `detail: "Este tenant no tiene Moodle Web Services configurado"`

#### Scenario: Error de Moodle WS retorna 502

- **WHEN** Moodle WS responde con error o está inaccesible
- **THEN** el sistema retorna 502 con el mensaje de error de Moodle
- **AND** no crea ninguna versión ni entrada

---

### Requirement: Aislamiento multi-tenant del padrón

El sistema SHALL garantizar que las operaciones de padrón (listado, carga, consulta) solo accedan a datos del tenant del usuario autenticado.

#### Scenario: Usuario de tenant B no puede ver padrón de tenant A

- **WHEN** un usuario del tenant B solicita GET `/api/padron/activo` con `materia_id` perteneciente al tenant A
- **THEN** el sistema retorna 404 (la materia no existe en el contexto del tenant B)

---

### Requirement: Descarte scope-isolated del padrón activo

El sistema SHALL permitir descartar el padrón activo de una materia/cohorte. El descarte SHALL afectar la versión activa completa para ese contexto del tenant. El sistema SHALL registrar la acción en `audit_log`.

#### Scenario: Descarte exitoso desactiva la versión activa

- **WHEN** un usuario con `padron:gestionar` hace DELETE `/api/padron/activo` con `materia_id` y `cohorte_id`
- **AND** existe una versión activa para ese contexto
- **THEN** la versión queda con `activa=false`
- **AND** el sistema retorna 200 con `entradas_descartadas` (count)
- **AND** registra `PADRON_CARGAR` con `operacion: "descarte"` en `audit_log`

#### Scenario: Descarte sin versión activa retorna 404

- **WHEN** no existe versión activa para (materia_id, cohorte_id)
- **AND** se intenta DELETE `/api/padron/activo`
- **THEN** el sistema retorna 404 con `detail: "No hay padrón activo para esta materia/cohorte"`

---

### Requirement: Consulta del padrón activo

El sistema SHALL proveer un endpoint para consultar la versión activa del padrón y sus entradas para una (materia, cohorte) del tenant. Requiere permiso `padron:gestionar`.

#### Scenario: Consulta devuelve entradas de la versión activa

- **WHEN** un usuario con `padron:gestionar` hace GET `/api/padron/activo` con `materia_id` y `cohorte_id`
- **AND** existe una versión activa con 5 entradas
- **THEN** el sistema retorna 200 con `version_id`, `cargado_at`, `entradas` (lista de 5 alumnos)
- **AND** los emails de las entradas aparecen descifrados en la respuesta

#### Scenario: Sin padrón activo retorna estructura vacía

- **WHEN** no existe versión activa para (materia_id, cohorte_id)
- **AND** se hace GET `/api/padron/activo`
- **THEN** el sistema retorna 200 con `version_id: null` y `entradas: []`

