## ADDED Requirements

### Requirement: Endpoint GET /api/perfil retorna el perfil propio decifrado

El sistema SHALL exponer `GET /api/perfil` que retorna los datos del `Usuario` correspondiente a la identidad del JWT. La identidad SHALL resolverse desde `auth_user_id` del modelo `Usuario` matcheando con `user.user_id` del JWT. Los campos PII cifrados (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) SHALL retornarse en plaintext, descifrados por la capa de encryption. No SHALL requerirse ningún permiso `modulo:accion` adicional a la autenticación.

#### Scenario: Usuario autenticado obtiene su propio perfil con PII en claro

- **WHEN** un usuario autenticado hace `GET /api/perfil`
- **THEN** el sistema responde HTTP 200 con el perfil del usuario
- **AND** los campos PII (email, cuil, cbu) están en plaintext, no cifrados
- **AND** el `id` retornado es el `usuario.id`, no el `auth_user.id`

#### Scenario: No se acepta usuario_id externo para consultar perfil ajeno

- **WHEN** una request a `GET /api/perfil` incluye cualquier parámetro `usuario_id`
- **THEN** el sistema ignora ese parámetro y retorna el perfil del usuario de la sesión
- **AND** no es posible obtener el perfil de otro usuario a través de este endpoint

#### Scenario: Usuario sin registro en tabla usuario recibe 404

- **WHEN** el JWT es válido pero no existe ningún `Usuario` con `auth_user_id` = `user.user_id`
- **THEN** el sistema responde HTTP 404

---

### Requirement: Endpoint PATCH /api/perfil actualiza campos editables, ignora CUIL

El sistema SHALL exponer `PATCH /api/perfil` que actualiza únicamente los campos editables del perfil propio: `nombre`, `apellidos`, `banco`, `cbu`, `alias_cbu`, `regional`, `legajo_profesional`, `facturador`. El campo `cuil` SHALL ser excluido del schema de request; si se incluye en el payload, SHALL ser ignorado silenciosamente. El sistema SHALL cifrar `cbu` y `alias_cbu` antes de persistir. No SHALL requerirse ningún permiso adicional a la autenticación.

#### Scenario: PATCH actualiza campos bancarios con cifrado

- **WHEN** el usuario hace `PATCH /api/perfil` con `{"cbu": "0070123400004208048300", "banco": "Galicia"}`
- **THEN** el sistema responde HTTP 200 con el perfil actualizado (cbu en plaintext)
- **AND** en la DB el campo `cbu_encrypted` difiere del valor enviado (cifrado)

#### Scenario: CUIL no se modifica aunque esté en el payload

- **WHEN** el usuario hace `PATCH /api/perfil` con `{"cuil": "20-99999999-9"}`
- **THEN** el sistema responde HTTP 200
- **AND** el campo `cuil` del usuario en la DB no ha cambiado

#### Scenario: PATCH parcial no borra campos no enviados

- **WHEN** el usuario hace `PATCH /api/perfil` con solo `{"banco": "Santander"}`
- **THEN** solo el campo `banco` se actualiza
- **AND** todos los demás campos del perfil mantienen sus valores previos

#### Scenario: Aislamiento — un usuario no puede actualizar el perfil de otro

- **WHEN** se intenta pasar un `id` o `usuario_id` externo en el body de `PATCH /api/perfil`
- **THEN** el sistema actualiza únicamente el perfil del usuario autenticado (ignora el campo)
