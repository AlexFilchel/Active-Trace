## Context

La plataforma necesita un padrón versionado de alumnos por (materia, cohorte) como prerequisito para calificaciones, análisis de atrasados y comunicaciones. El modelo previo no tiene tablas de padrón; este change las introduce desde cero. Dos fuentes de datos posibles: archivo xlsx/csv exportado desde Moodle, o Moodle Web Services directamente. El email del alumno es PII y va cifrado en reposo (AES-256). Un alumno puede existir en el padrón antes de tener cuenta `usuario` en el sistema (usuario_id nullable).

## Goals / Non-Goals

**Goals**:
- Modelo `VersionPadron` + `EntradaPadron` con migración Alembic
- Ingesta desde archivo (.xlsx / .csv) en formato estándar Moodle
- Integración con Moodle WS como fuente alternativa (opcional por tenant)
- Activación/desactivación de versiones (una activa por contexto)
- Descarte scope-isolated (RN-04): borra versión activa + entradas del usuario actor
- Auditoría de carga (`PADRON_CARGAR`)

**Non-Goals**:
- Merge de versiones parciales — la carga siempre reemplaza (RN-05)
- UI de gestión de padrones (es C-22/C-23)
- Importar calificaciones (es C-10)
- Sincronización automática / polling de Moodle

## Decisions

### D1: Modelo de versionado — nueva versión desactiva la anterior (no hard delete)

**Decisión**: `VersionPadron.activa` (booleano). Al activar una nueva versión, se hace `UPDATE SET activa=false WHERE materia_id=X AND cohorte_id=Y AND tenant_id=Z AND activa=true`. No se borra la anterior.

**Alternativas descartadas**:
- Hard delete del padrón anterior: pierde historial, viola auditoría.
- Versión como campo numérico incremental: más complejo para queries; el booleano es suficiente dado el acceso pattern.

### D2: Parsing de archivo — detección de columnas por nombre, no por posición

**Decisión**: El parser busca headers por nombre (case-insensitive, normalizando espacios y tildes): `Nombre`, `Apellido(s)`, `Dirección de correo`, `Grupos`. Si alguna columna obligatoria no se encuentra, la ingesta falla con 422 y lista las columnas faltantes.

**Alternativas descartadas**:
- Posición fija: frágil ante cambios de exportación de Moodle.
- Schema externo configurable: innecesaria complejidad para MVP.

### D3: Moodle WS — cliente `httpx` async, lazy-loaded por tenant

**Decisión**: `MoodleWSClient` en `backend/app/integrations/moodle_ws.py` usa `httpx.AsyncClient`. La URL del WS y el token son campos del `Tenant` (almacenados cifrados). Si el tenant no tiene WS configurado, el endpoint retorna 422 indicando que solo se acepta archivo.

**Alternativas descartadas**:
- `requests` síncrono con `run_in_executor`: añade complejidad sin beneficio.
- Cliente compartido entre tenants: viola multi-tenancy; cada tenant tiene su propio token.

### D4: Cifrado del email — `email_encrypted` (AES-256) + `email_hash` (para lookup)

**Decisión**: Misma convención que `Usuario.email_encrypted`/`email_hash`. El hash permite buscar si una `EntradaPadron` ya tiene `usuario_id` asociado sin descifrar en bulk.

### D5: Permiso requerido — `padron:gestionar`

**Decisión**: tanto PROFESOR (sobre sus materias) como COORDINADOR pueden cargar padrones. Se usa un permiso único `padron:gestionar`; la restricción PROFESOR-solo-sus-materias se valida en el service comparando la asignación del actor con la materia solicitada.

### D6: Descarte scope-isolated (RN-04) — solo afecta versión activa del actor

**Decisión**: `DELETE /api/padron/activo` recibe `(materia_id, cohorte_id)` y desactiva la versión activa del tenant. Como en el MVP un solo padrón rige por materia/cohorte, el descarte es efectivo para todos. Se registra `PADRON_CARGAR` con `operacion: "descarte"` en audit.

## Risks / Trade-offs

- [Email PII en EntradaPadron] Cifrado en aplicación (no en DB) → riesgo si la clave de cifrado se rota sin re-cifrar datos existentes → Mitigación: usar misma clave gestionada por `settings.ENCRYPTION_KEY`; documentar en runbook de rotación.
- [usuario_id nullable] El padrón puede tener alumnos sin cuenta → al cruzar calificaciones, C-10 debe tolerar entradas sin `usuario_id` → se documenta en el modelo.
- [Moodle WS opcional] Los tenants sin WS configurado usan solo archivo → el endpoint distingue ambos flujos por presencia de `moodle_ws_url` en el tenant; si ninguno aplica, retorna 422 claro.

## Migration Plan

1. `alembic upgrade 005_padron` — crea tablas `version_padron` y `entrada_padron`.
2. No hay datos previos que migrar (tablas nuevas).
3. Rollback: `alembic downgrade 004_audit_log` — drop en cascada de `entrada_padron` → `version_padron`.

## Open Questions

*(ninguna — todas las decisiones cerradas arriba)*
