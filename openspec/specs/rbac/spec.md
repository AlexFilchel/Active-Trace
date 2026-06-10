### Requirement: Catálogo de roles por tenant
El sistema SHALL mantener una tabla `Rol` por tenant con campos: `id` (UUID), `tenant_id`, `nombre` (string), `descripcion` (string, opcional), más los campos de auditoría del `TenantScopedMixin` (created_at, updated_at, deleted_at). La unicidad de `(tenant_id, nombre)` SHALL ser enforceada a nivel DB.

#### Scenario: Rol duplicado en el mismo tenant es rechazado
- **WHEN** se intenta insertar un rol con el mismo `nombre` y `tenant_id` que uno existente
- **THEN** la base de datos rechaza la inserción con violación de constraint de unicidad

#### Scenario: El mismo nombre de rol puede existir en tenants distintos
- **WHEN** dos tenants distintos tienen un rol con el mismo nombre (ej. "PROFESOR")
- **THEN** ambos registros coexisten sin conflicto y cada uno pertenece a su tenant

---

### Requirement: Catálogo de permisos por tenant
El sistema SHALL mantener una tabla `Permiso` con campos: `id` (UUID), `tenant_id`, `nombre` (string en formato `modulo:accion`, máx 64 chars). La unicidad de `(tenant_id, nombre)` SHALL ser enforceada a nivel DB.

#### Scenario: Permiso con formato modulo:accion es aceptado
- **WHEN** se inserta un permiso con nombre `calificaciones:importar` para un tenant
- **THEN** el registro se persiste correctamente

#### Scenario: Permiso duplicado en el mismo tenant es rechazado
- **WHEN** se intenta insertar un permiso con el mismo `nombre` y `tenant_id` que uno existente
- **THEN** la base de datos rechaza la inserción con violación de constraint de unicidad

---

### Requirement: Matriz rol × permiso por tenant
El sistema SHALL mantener una tabla `RolPermiso` que asocia `Rol` con `Permiso` mediante `(rol_id, permiso_id)` como clave compuesta única. Ambas FK deben pertenecer al mismo `tenant_id`.

#### Scenario: Un rol puede tener múltiples permisos asignados
- **WHEN** se asignan tres permisos distintos al rol PROFESOR en un tenant
- **THEN** el rol PROFESOR tiene exactamente esos tres permisos efectivos en ese tenant

#### Scenario: La asociación duplicada es rechazada
- **WHEN** se intenta insertar la misma combinación `(rol_id, permiso_id)` dos veces
- **THEN** la base de datos rechaza la segunda inserción con violación de unicidad

---

### Requirement: Seed de roles del dominio y matriz base
La migración `003_rbac` SHALL insertar los 7 roles del dominio y sus permisos base (según la matriz §3.3 de `knowledge-base/03_actores_y_roles.md`) para todos los tenants existentes. El seed SHALL ser idempotente (`INSERT ... ON CONFLICT DO NOTHING`).

Roles del dominio a sembrar: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS.

#### Scenario: Seed ejecutado en DB con tenants existentes
- **WHEN** se ejecuta `alembic upgrade 003_rbac` con uno o más tenants en la DB
- **THEN** cada tenant tiene los 7 roles y todos sus permisos base asociados

#### Scenario: Seed es idempotente ante re-ejecución
- **WHEN** la migración se ejecuta dos veces (ej. en tests)
- **THEN** no se duplican datos y no se produce ningún error

---

### Requirement: Resolución de permisos efectivos server-side
El sistema SHALL resolver los permisos efectivos de un usuario en cada request a partir de los nombres de rol del JWT claim `roles`, consultando la DB para obtener la unión de permisos de todos sus roles dentro de su tenant.

#### Scenario: Usuario con un rol resuelve sus permisos correctamente
- **WHEN** un usuario autenticado tiene el rol PROFESOR en su JWT
- **THEN** el sistema resuelve el conjunto de permisos asignados al rol PROFESOR en ese tenant

#### Scenario: Usuario con múltiples roles recibe la unión de permisos
- **WHEN** un usuario autenticado tiene los roles PROFESOR y COORDINADOR en su JWT
- **THEN** el sistema resuelve la unión de permisos de ambos roles (sin duplicados)

#### Scenario: Usuario sin ningún rol asignado no tiene permisos
- **WHEN** un usuario autenticado tiene `roles: []` en su JWT
- **THEN** el sistema resuelve un conjunto de permisos vacío

---

### Requirement: Guard require_permission fail-closed
El sistema SHALL proporcionar una dependencia FastAPI `require_permission("modulo:accion")` que verifica si el usuario autenticado tiene el permiso requerido. Si no lo tiene, SHALL retornar HTTP 403. Si el usuario no está autenticado, SHALL retornar HTTP 401 (delegado a `get_current_user`).

#### Scenario: Usuario con permiso accede al endpoint
- **WHEN** un usuario con rol PROFESOR (que tiene `calificaciones:importar`) accede a un endpoint que declara `require_permission("calificaciones:importar")`
- **THEN** el acceso es concedido y el handler se ejecuta

#### Scenario: Usuario sin el permiso recibe 403
- **WHEN** un usuario con rol ALUMNO (que no tiene `calificaciones:importar`) accede a un endpoint que declara `require_permission("calificaciones:importar")`
- **THEN** el sistema retorna HTTP 403 sin ejecutar el handler

#### Scenario: Usuario no autenticado recibe 401
- **WHEN** una petición sin Authorization header accede a un endpoint que declara `require_permission("equipos:asignar")`
- **THEN** el sistema retorna HTTP 401

#### Scenario: Permiso requerido no existente en seed resulta en 403
- **WHEN** un endpoint declara `require_permission("modulo:accion_inexistente")` y ningún rol del usuario tiene ese permiso
- **THEN** el sistema retorna HTTP 403 (fail-closed: la ausencia de permiso es denegación)

---

### Requirement: Aislamiento multi-tenant de permisos
El sistema SHALL garantizar que la resolución de permisos de un usuario de un tenant nunca incluya roles o permisos de otro tenant.

#### Scenario: Roles de tenant A no otorgan permisos en tenant B
- **WHEN** un usuario del tenant A tiene el rol ADMIN (con todos sus permisos)
- **THEN** si ese mismo usuario intenta acceder a un endpoint del tenant B, sus permisos se resuelven con los roles de tenant B (no de A), resultando en 403 si el tenant B no tiene ese usuario/rol
