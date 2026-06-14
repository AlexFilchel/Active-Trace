# Spec: avisos-y-acknowledgment

Módulo de avisos institucionales multi-tenant con segmentación de audiencia, ventana de vigencia y confirmación de lectura auditable.

---

## ADDED Requirements

### Requirement: Modelo de datos — Aviso

**ID**: AVI-01
**Tipo**: Data Model

El sistema persiste la entidad `Aviso` con los siguientes atributos:

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id` | UUID PK | auto |
| `tenant_id` | UUID FK→Tenant | NOT NULL, índice |
| `alcance` | enum | `Global \| PorMateria \| PorCohorte \| PorRol` |
| `materia_id` | UUID FK→Materia | nullable; requerido si alcance=PorMateria |
| `cohorte_id` | UUID FK→Cohorte | nullable; requerido si alcance=PorCohorte |
| `rol_destino` | varchar(50) | nullable; requerido si alcance=PorRol |
| `severidad` | enum | `Info \| Advertencia \| Crítico` |
| `titulo` | varchar(255) | NOT NULL |
| `cuerpo` | text | NOT NULL |
| `inicio_en` | timestamptz | NOT NULL |
| `fin_en` | timestamptz | NOT NULL; fin_en > inicio_en |
| `orden` | int | NOT NULL, default 0 |
| `activo` | bool | NOT NULL, default true |
| `requiere_ack` | bool | NOT NULL, default false |
| `created_at` | timestamptz | auto |
| `updated_at` | timestamptz | auto |
| `deleted_at` | timestamptz | nullable (soft delete) |

**Restricciones adicionales**:
- `fin_en` DEBE ser posterior a `inicio_en`; violar esto es error de validación (422).
- `materia_id` solo se evalúa cuando `alcance = PorMateria`; se ignora en otros alcances.
- `cohorte_id` solo se evalúa cuando `alcance = PorCohorte`.
- `rol_destino` solo se evalúa cuando `alcance = PorRol`.

---

### Requirement: Modelo de datos — AcknowledgmentAviso

**ID**: AVI-02
**Tipo**: Data Model

El sistema persiste la entidad `AcknowledgmentAviso`:

| Atributo | Tipo | Restricciones |
|---|---|---|
| `id` | UUID PK | auto |
| `tenant_id` | UUID FK→Tenant | NOT NULL |
| `aviso_id` | UUID FK→Aviso | NOT NULL, índice |
| `usuario_id` | UUID FK→Usuario | NOT NULL, índice |
| `confirmado_at` | timestamptz | NOT NULL, default now() |
| `created_at` | timestamptz | auto |
| `deleted_at` | timestamptz | nullable |

**Restricción única**: `(tenant_id, aviso_id, usuario_id)` — un usuario solo puede acusar un aviso una vez.

**Contadores derivados**: `total_acks` y `total_destinatarios` se calculan en tiempo de consulta mediante COUNT sobre `acknowledgment_aviso`; NO se almacenan como columnas denormalizadas (RN-19).

---

### Requirement: Permiso avisos:publicar

**ID**: AVI-03
**Tipo**: Authorization

- El permiso `avisos:publicar` habilita crear, editar y desactivar avisos.
- Se asigna por defecto a los roles `COORDINADOR` y `ADMIN` en cada tenant (seed idempotente en migración 012).
- La visualización y el ack no requieren permiso especial; todos los usuarios autenticados pueden leer sus avisos y acusar recibo.

---

### Requirement: Creación y gestión de avisos (ABM)

**ID**: AVI-04
**Tipo**: Functional

**Crear aviso** (`POST /api/avisos`):
- Requiere permiso `avisos:publicar`.
- Payload: `alcance`, `severidad`, `titulo`, `cuerpo`, `inicio_en`, `fin_en`, `orden`, `activo`, `requiere_ack`; más `materia_id` / `cohorte_id` / `rol_destino` según alcance.
- Valida `fin_en > inicio_en`; error 422 si no se cumple.
- Responde 201 con el aviso creado.
- Audita `AVISO_CREAR`.

**Editar aviso** (`PATCH /api/avisos/{id}`):
- Requiere permiso `avisos:publicar`.
- Permite actualizar cualquier campo (excepto `id`, `tenant_id`, `created_at`).
- Responde 200 con aviso actualizado.
- Audita `AVISO_EDITAR`.

**Desactivar aviso** (`PATCH /api/avisos/{id}` con `{"activo": false}`):
- No hace soft delete; solo marca `activo = false`. El aviso deja de ser visible inmediatamente.

**Listar avisos (gestión)** (`GET /api/avisos/gestion`):
- Requiere `avisos:publicar`.
- Devuelve TODOS los avisos del tenant (activos e inactivos, dentro y fuera de vigencia).
- Incluye métricas derivadas: `total_acks` (count de acknowledgments activos).

---

### Requirement: Visualización segmentada por destinatario (RN-18, RN-20)

**ID**: AVI-05
**Tipo**: Functional

**Listar mis avisos** (`GET /api/avisos`):
- Disponible para cualquier usuario autenticado.
- Filtra por:
  1. `activo = true`
  2. `inicio_en <= now() <= fin_en` (ventana de vigencia — RN-18)
  3. Audiencia del usuario (RN-20): el aviso se muestra si **alguna** de las siguientes condiciones se cumple:
     - `alcance = Global`
     - `alcance = PorRol` Y `rol_destino` es uno de los roles del usuario en el tenant
     - `alcance = PorMateria` Y el usuario tiene una asignación vigente a esa `materia_id`
     - `alcance = PorCohorte` Y el usuario tiene una asignación vigente a esa `cohorte_id`
  4. Si `requiere_ack = true`: excluir avisos que el usuario ya haya acusado (a menos que el parámetro `?incluir_acusados=true` esté presente).
- Ordena por `orden ASC`, luego `inicio_en DESC`.
- Responde lista de `AvisoResponse` con campo `acusado: bool` derivado.

---

### Requirement: Confirmación de lectura — Ack (RN-19)

**ID**: AVI-06
**Tipo**: Functional

**Acusar recibo** (`POST /api/avisos/{id}/ack`):
- Disponible para cualquier usuario autenticado.
- Valida que el aviso exista, esté activo, en vigencia y tenga `requiere_ack = true`; si no cumple → 422.
- Si el usuario ya acusó el aviso → responde 200 idempotente (no crea duplicado).
- Si no acusó → crea `AcknowledgmentAviso` y responde 201.
- Audita `AVISO_ACK`.
- Tras el ack, el aviso ya no aparece en `GET /api/avisos` del usuario (a menos que `?incluir_acusados=true`).

---

### Requirement: Métricas de aviso

**ID**: AVI-07
**Tipo**: Functional

**Métricas** (`GET /api/avisos/{id}/metricas`):
- Requiere `avisos:publicar`.
- Devuelve: `total_acks` (COUNT acknowledgments activos), `aviso_id`, `titulo`, `requiere_ack`.
- Los contadores son siempre derivados (COUNT en tiempo real), nunca denormalizados.

---

### Requirement: Aislamiento multi-tenant

**ID**: AVI-08
**Tipo**: Non-Functional

- Todos los endpoints filtran por `tenant_id` del JWT.
- Un usuario de tenant A nunca puede leer ni acusar avisos de tenant B.
- Intentar acceder a un aviso de otro tenant responde 404 (no revela existencia).
