## ADDED Requirements

### Requirement: Modelo Usuario con PII cifrada y aislamiento tenant
El sistema SHALL mantener una tabla `usuario` tenant-scoped con `id` UUID, `tenant_id`, timestamps, `deleted_at`, `auth_user_id` nullable, `nombre`, `apellidos`, datos PII cifrados (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`), `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador` y `estado` (`Activo` | `Inactivo`). Los campos PII SHALL persistirse cifrados en reposo y SHALL NOT aparecer en logs ni en columnas plaintext.

#### Scenario: PII no se persiste como plaintext
- **WHEN** se crea un usuario con email, DNI, CUIL, CBU y alias CBU
- **THEN** las columnas persistidas para esos datos difieren del plaintext enviado
- **AND** no existen columnas plaintext para esos valores sensibles

#### Scenario: Unicidad de email por tenant con email cifrado
- **WHEN** se intenta crear dos usuarios con el mismo email normalizado dentro del mismo tenant
- **THEN** el sistema rechaza el segundo con HTTP 409 o violación de unicidad controlada

#### Scenario: Mismo email en tenants distintos coexiste
- **WHEN** dos tenants crean usuarios con el mismo email normalizado
- **THEN** ambos usuarios se persisten sin conflicto y permanecen aislados por tenant

#### Scenario: Legajo no actúa como identidad de sesión
- **WHEN** una request incluye `legajo` o `usuario_id` en body/query/path
- **THEN** esos valores se tratan solo como datos de negocio
- **AND** no modifican el actor autenticado ni el tenant resuelto desde JWT

---

### Requirement: Modelo Asignacion con rol, contexto académico y vigencia temporal
El sistema SHALL mantener una tabla `asignacion` tenant-scoped que vincula `usuario_id` con `rol_id` y contexto académico opcional (`materia_id`, `carrera_id`, `cohorte_id`, `comisiones`), más `responsable_id`, `desde` y `hasta`. `estado_vigencia` SHALL ser derivado desde fechas, no persistido como fuente de verdad.

#### Scenario: Asignacion vigente es identificada por rango de fechas
- **WHEN** `desde <= hoy` y (`hasta` es nulo o `hasta >= hoy`)
- **THEN** la asignación se considera `Vigente`

#### Scenario: Asignacion vencida conserva histórico
- **WHEN** `hasta < hoy`
- **THEN** la asignación se considera `Vencida`
- **AND** permanece consultable como histórico
- **AND** no otorga permisos efectivos

#### Scenario: Contexto académico debe pertenecer al mismo tenant
- **WHEN** se crea una asignación con `materia_id`, `carrera_id` o `cohorte_id` perteneciente a otro tenant
- **THEN** el sistema rechaza la operación o responde 404/422 fail-closed

#### Scenario: Responsable debe pertenecer al mismo tenant
- **WHEN** `responsable_id` referencia un usuario de otro tenant
- **THEN** el sistema rechaza la asignación

---

### Requirement: ABM de usuarios protegido por permiso usuarios:gestionar
El sistema SHALL exponer endpoints `GET/POST /api/admin/usuarios` y `GET/PATCH/DELETE /api/admin/usuarios/{id}`. Todos SHALL requerir `require_permission("usuarios:gestionar")`. Un usuario sin ese permiso SHALL recibir HTTP 403.

#### Scenario: Crear usuario con permiso devuelve 201
- **WHEN** un ADMIN con `usuarios:gestionar` envía un payload válido
- **THEN** el sistema crea el usuario en el tenant del JWT y devuelve HTTP 201
- **AND** la respuesta no incluye campos internos `*_encrypted` ni `*_hash`

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario autenticado sin `usuarios:gestionar` llama al ABM de usuarios
- **THEN** el sistema devuelve HTTP 403

#### Scenario: Listado de usuarios respeta tenant
- **WHEN** un ADMIN lista usuarios
- **THEN** solo recibe usuarios de su tenant autenticado

---

### Requirement: CRUD de asignaciones protegido por permiso equipos:asignar
El sistema SHALL exponer endpoints `GET/POST /api/asignaciones` y `GET/PATCH/DELETE /api/asignaciones/{id}`. Todos SHALL requerir `require_permission("equipos:asignar")`.

#### Scenario: Crear asignacion con contexto válido devuelve 201
- **WHEN** un COORDINADOR o ADMIN con `equipos:asignar` crea una asignación para usuario, rol y contexto del mismo tenant
- **THEN** el sistema devuelve HTTP 201 con `estado_vigencia` derivado

#### Scenario: Listado soporta filtros por usuario, rol y contexto
- **WHEN** el cliente llama `GET /api/asignaciones` con filtros de `usuario_id`, `rol_id`, `materia_id`, `carrera_id` o `cohorte_id`
- **THEN** la respuesta incluye solo asignaciones del tenant que cumplen los filtros

#### Scenario: Soft delete de asignacion preserva histórico
- **WHEN** se elimina una asignación
- **THEN** se marca `deleted_at`
- **AND** deja de aparecer en listados activos por defecto

---

### Requirement: Permisos efectivos consideran vigencia de asignaciones
El sistema SHALL garantizar que una asignación vencida no otorgue permisos efectivos. La autorización contextual SHALL consultar únicamente asignaciones no eliminadas, del mismo tenant y vigentes a la fecha de la request.

#### Scenario: Asignacion vencida no autoriza
- **WHEN** un usuario tiene una asignación con rol que normalmente otorga un permiso, pero `hasta < hoy`
- **THEN** `require_permission` o la verificación contextual deniega el acceso con HTTP 403

#### Scenario: Multiples asignaciones vigentes unionan permisos
- **WHEN** un usuario tiene múltiples asignaciones vigentes con roles distintos
- **THEN** sus permisos efectivos son la unión de los permisos de esos roles dentro del tenant

#### Scenario: Tenant ajeno no aporta permisos
- **WHEN** existen roles o asignaciones similares en otro tenant
- **THEN** no se consideran para la autorización del usuario actual

---

### Requirement: Schemas Pydantic v2 rechazan campos no declarados
Los schemas de request/response para `Usuario` y `Asignacion` SHALL usar `model_config = ConfigDict(extra='forbid')`. Los requests SHALL NOT aceptar `tenant_id`, campos `*_encrypted`, campos `*_hash` ni cualquier identificador que pretenda sobrescribir la identidad autenticada.

#### Scenario: Request con tenant_id es rechazado
- **WHEN** un cliente envía `tenant_id` en el body de creación o actualización
- **THEN** el sistema devuelve HTTP 422 por campo extra no permitido

#### Scenario: Request con campos internos de cifrado es rechazado
- **WHEN** un cliente envía `email_hash` o `email_encrypted`
- **THEN** el sistema devuelve HTTP 422

#### Scenario: Fechas inválidas son rechazadas
- **WHEN** una asignación tiene `hasta` anterior a `desde`
- **THEN** el sistema devuelve HTTP 422

---

### Requirement: Migracion 005 crea usuarios, asignaciones y permisos base
La migración `005_usuarios_asignaciones` SHALL crear las tablas `usuario` y `asignacion` con constraints e índices necesarios, y SHALL sembrar de forma idempotente los permisos `usuarios:gestionar` y `equipos:asignar` en los roles correspondientes.

#### Scenario: Migracion crea tablas requeridas
- **WHEN** se ejecuta `alembic upgrade 005_usuarios_asignaciones`
- **THEN** existen las tablas `usuario` y `asignacion` con sus FKs, índices y constraints

#### Scenario: Seed de permisos es idempotente
- **WHEN** la migración o su lógica de seed se ejecuta más de una vez
- **THEN** no duplica `permiso` ni `rol_permiso`

#### Scenario: Roles esperados reciben permisos
- **WHEN** la migración se aplica a un tenant con roles base
- **THEN** ADMIN tiene `usuarios:gestionar`
- **AND** ADMIN y COORDINADOR tienen `equipos:asignar`
