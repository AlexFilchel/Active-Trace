## ADDED Requirements

### Requirement: Modelo Carrera con aislamiento tenant y unicidad de código
El sistema SHALL mantener una tabla `carrera` con campos: `id` (UUID), `tenant_id` (UUID, FK → tenant), `codigo` (string, ≤50 chars), `nombre` (string, ≤200 chars), `estado` (string: "Activa" | "Inactiva"), más los campos de auditoría del `TenantScopedMixin` (created_at, updated_at, deleted_at). La unicidad de `(tenant_id, codigo)` SHALL ser enforceada a nivel DB. El estado inicial de una nueva carrera SHALL ser "Activa".

#### Scenario: Unicidad de código por tenant es enforceada
- **WHEN** se intenta crear una carrera con el mismo `codigo` y `tenant_id` que una carrera existente (no borrada)
- **THEN** la base de datos rechaza la inserción con violación de constraint de unicidad

#### Scenario: El mismo código puede existir en tenants distintos
- **WHEN** dos tenants distintos crean una carrera con el mismo `codigo` (ej. "TUPAD")
- **THEN** ambos registros coexisten sin conflicto y cada uno pertenece a su tenant

#### Scenario: Carrera creada con estado Activa por defecto
- **WHEN** se crea una carrera sin especificar estado
- **THEN** su estado es "Activa"

#### Scenario: Soft delete preserva el registro en DB
- **WHEN** se ejecuta DELETE sobre una carrera
- **THEN** el campo `deleted_at` se establece con el timestamp actual y la carrera deja de aparecer en listados, pero el registro persiste en la tabla

---

### Requirement: Modelo Cohorte con FK a Carrera y unicidad compuesta
El sistema SHALL mantener una tabla `cohorte` con campos: `id` (UUID), `tenant_id`, `carrera_id` (UUID, FK → carrera, NOT NULL), `nombre` (string, ≤100 chars), `anio` (integer, NOT NULL), `vig_desde` (date, NOT NULL), `vig_hasta` (date, nullable — nulo = vigencia abierta), `estado` (string: "Activa" | "Inactiva"). La unicidad de `(tenant_id, carrera_id, nombre)` SHALL ser enforceada a nivel DB. El estado inicial SHALL ser "Activa".

#### Scenario: Unicidad compuesta (tenant, carrera, nombre) es enforceada
- **WHEN** se intenta crear una cohorte con el mismo `tenant_id`, `carrera_id` y `nombre`
- **THEN** la base de datos rechaza la inserción con violación de constraint de unicidad

#### Scenario: Cohortes con igual nombre en distintas carreras del mismo tenant coexisten
- **WHEN** dos carreras del mismo tenant tienen cada una una cohorte con el mismo nombre (ej. "MAR-2026")
- **THEN** ambos registros coexisten sin conflicto

#### Scenario: Cohorte requiere FK válida a carrera del mismo tenant
- **WHEN** se intenta crear una cohorte con un `carrera_id` que pertenece a otro tenant
- **THEN** la operación falla con error de integridad referencial o aislamiento de tenant

---

### Requirement: Modelo Materia con unicidad de código por tenant
El sistema SHALL mantener una tabla `materia` con campos: `id` (UUID), `tenant_id`, `codigo` (string, ≤50 chars), `nombre` (string, ≤200 chars), `estado` (string: "Activa" | "Inactiva"). La unicidad de `(tenant_id, codigo)` SHALL ser enforceada a nivel DB. Es el catálogo único de materias del tenant — no existen catálogos paralelos.

#### Scenario: Unicidad de código de materia por tenant es enforceada
- **WHEN** se intenta crear una materia con el mismo `codigo` y `tenant_id` que una materia existente
- **THEN** la base de datos rechaza la inserción con violación de constraint de unicidad

#### Scenario: El mismo código de materia puede existir en tenants distintos
- **WHEN** dos tenants crean materias con igual `codigo`
- **THEN** ambos registros coexisten sin conflicto

#### Scenario: Materia creada con estado Activa por defecto
- **WHEN** se crea una materia sin especificar estado
- **THEN** su estado es "Activa"

---

### Requirement: Regla de negocio — carrera inactiva no admite nuevas cohortes activas
El sistema SHALL rechazar la creación de una cohorte en estado "Activa" si su carrera asociada tiene estado "Inactiva". El rechazo SHALL ocurrir en la capa de servicio con HTTP 422 Unprocessable Entity.

#### Scenario: Intento de crear cohorte activa en carrera inactiva
- **WHEN** se intenta crear una cohorte con `estado="Activa"` para una carrera cuyo `estado="Inactiva"`
- **THEN** el sistema devuelve HTTP 422 con mensaje indicando que la carrera está inactiva

#### Scenario: Crear cohorte en carrera activa funciona correctamente
- **WHEN** se crea una cohorte para una carrera con `estado="Activa"`
- **THEN** la cohorte se persiste y el sistema devuelve HTTP 201 con los datos de la cohorte creada

#### Scenario: Cohortes existentes no se afectan al inactivar su carrera
- **WHEN** una carrera con cohortes activas cambia a estado "Inactiva"
- **THEN** las cohortes existentes mantienen su estado sin cambios

---

### Requirement: Endpoints ABM de Carrera con guard de permiso
El sistema SHALL exponer los endpoints `GET /api/admin/carreras`, `POST /api/admin/carreras`, `GET /api/admin/carreras/{id}`, `PATCH /api/admin/carreras/{id}`, `DELETE /api/admin/carreras/{id}`. Todos los endpoints SHALL requerir el permiso `estructura:gestionar`. Un usuario sin ese permiso SHALL recibir HTTP 403.

#### Scenario: Usuario sin permiso estructura:gestionar recibe 403
- **WHEN** un usuario autenticado sin el permiso `estructura:gestionar` llama a cualquier endpoint bajo `/api/admin/carreras`
- **THEN** el sistema devuelve HTTP 403 Forbidden

#### Scenario: Listar carreras devuelve solo las del tenant del usuario autenticado
- **WHEN** un usuario con permiso `estructura:gestionar` llama a `GET /api/admin/carreras`
- **THEN** la respuesta incluye solo carreras con `tenant_id` del usuario autenticado, sin carreras de otros tenants

#### Scenario: Crear carrera devuelve 201 con datos completos
- **WHEN** un usuario con permiso crea una carrera válida con `codigo` y `nombre`
- **THEN** el sistema responde HTTP 201 y el body incluye `id`, `codigo`, `nombre`, `estado`, `tenant_id`

#### Scenario: Actualizar carrera con datos válidos devuelve 200
- **WHEN** un usuario con permiso envía PATCH a `/api/admin/carreras/{id}` con un `nombre` actualizado
- **THEN** el sistema responde HTTP 200 y el body refleja el nombre actualizado

#### Scenario: Obtener carrera de otro tenant devuelve 404
- **WHEN** un usuario autenticado intenta GET de una carrera perteneciente a otro tenant
- **THEN** el sistema devuelve HTTP 404 (el registro no es visible fuera del tenant)

---

### Requirement: Endpoints ABM de Cohorte con guard de permiso
El sistema SHALL exponer `GET/POST /api/admin/cohortes` y `GET/PATCH/DELETE /api/admin/cohortes/{id}`, todos con guard `estructura:gestionar`. Los listados SHALL soportar filtro opcional por `carrera_id`.

#### Scenario: Listar cohortes filtrando por carrera_id
- **WHEN** un usuario con permiso llama a `GET /api/admin/cohortes?carrera_id={id}`
- **THEN** la respuesta incluye solo cohortes de esa carrera dentro del tenant del usuario

#### Scenario: Cohorte de otro tenant no es visible
- **WHEN** un usuario autenticado solicita GET de una cohorte de otro tenant
- **THEN** el sistema devuelve HTTP 404

---

### Requirement: Endpoints ABM de Materia con guard de permiso
El sistema SHALL exponer `GET/POST /api/admin/materias` y `GET/PATCH/DELETE /api/admin/materias/{id}`, todos con guard `estructura:gestionar`. El listado SHALL soportar filtro opcional por `estado`.

#### Scenario: Listar materias activas filtrando por estado
- **WHEN** un usuario con permiso llama a `GET /api/admin/materias?estado=Activa`
- **THEN** la respuesta incluye solo materias con `estado="Activa"` del tenant del usuario

#### Scenario: Materia de otro tenant no es visible
- **WHEN** un usuario autenticado solicita GET de una materia de otro tenant
- **THEN** el sistema devuelve HTTP 404

---

### Requirement: Schemas Pydantic v2 con extra='forbid'
Los schemas de request y response para Carrera, Cohorte y Materia SHALL ser Pydantic v2 con `model_config = ConfigDict(extra='forbid')`. El campo `tenant_id` NO SHALL exponerse en schemas de request (se inyecta desde el JWT). Campos de auditoría (`created_at`, `updated_at`) solo aparecen en responses de lectura.

#### Scenario: Request con campo desconocido es rechazado
- **WHEN** un cliente envía un POST con un campo no declarado en el schema (ej. `tenant_id` en el body)
- **THEN** el sistema devuelve HTTP 422 con error de validación

#### Scenario: tenant_id no es aceptado en el body del request
- **WHEN** un cliente envía `{"codigo": "X", "nombre": "Y", "tenant_id": "..."}` en un POST
- **THEN** el sistema devuelve HTTP 422 (campo extra no permitido)

---

### Requirement: Migración 004 con seed del permiso estructura:gestionar
La migración `004_estructura_academica` SHALL: (1) crear las tablas `carrera`, `cohorte`, `materia` con sus constraints e índices; (2) sembrar el permiso `estructura:gestionar` y asociarlo al rol ADMIN en todos los tenants existentes. El seed SHALL ser idempotente (`INSERT ... ON CONFLICT DO NOTHING`).

#### Scenario: Migración 004 crea las tres tablas
- **WHEN** se ejecuta `alembic upgrade 004_estructura_academica`
- **THEN** las tablas `carrera`, `cohorte` y `materia` existen en la DB con todos sus campos y constraints

#### Scenario: Seed del permiso es idempotente
- **WHEN** la migración se ejecuta dos veces (ej. en tests)
- **THEN** no se duplican registros de permiso ni de rol_permiso y no se produce ningún error

#### Scenario: El rol ADMIN del tenant tiene el permiso estructura:gestionar tras la migración
- **WHEN** se ejecuta la migración con un tenant que tiene rol ADMIN
- **THEN** el rol ADMIN del tenant tiene el permiso `estructura:gestionar` en su matriz RolPermiso
