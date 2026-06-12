## Why

El sistema necesita saber quiénes son los alumnos de cada materia/cohorte antes de poder cruzar calificaciones, detectar atrasados o disparar comunicaciones. Sin padrón cargado, todas las funcionalidades de análisis (C-10, C-11, C-12) quedan bloqueadas. C-09 introduce el modelo `VersionPadron` + `EntradaPadron`, la ingesta desde archivo (xlsx/csv Moodle export) y la integración con Moodle Web Services para tenants que lo expongan.

## What Changes

- **Nuevos modelos**: `VersionPadron` y `EntradaPadron` con migración Alembic `005_padron.py`.
- **Ingesta por archivo**: endpoint que acepta `.xlsx` / `.csv` en el formato de exportación estándar de Moodle; detecta columnas Nombre, Apellido, Email y Grupos/Comisión.
- **Versionado destructivo**: al cargar un padrón nuevo, la versión anterior se desactiva (no se borra); solo una versión está activa por `(tenant_id, materia_id, cohorte_id)` en cada momento (RN-05).
- **Integración Moodle WS**: cliente `moodle_ws.py` que consume `core_enrol_get_enrolled_users` para tenants que exponen la API; la ingesta manual por archivo es el fallback.
- **Endpoint de descarte por materia**: borra el padrón activo y calificaciones asociadas en scope aislado al usuario (RN-04) — prepara el terreno para C-10.
- **Auditoría**: acción `PADRON_CARGAR` registrada en `audit_log` por cada carga.

## Capabilities

### New Capabilities

- `padron-ingesta`: gestión del padrón versionado de alumnos por materia/cohorte — carga desde archivo o Moodle WS, activación/desactivación de versiones, descarte scope-isolated.

### Modified Capabilities

*(ninguna — nueva capacidad sin cambios en specs existentes)*

## Impact

- **Backend/models**: `backend/app/models/padron.py` — `VersionPadron`, `EntradaPadron`
- **Backend/migrations**: `backend/alembic/versions/005_padron.py`
- **Backend/repositories**: `backend/app/repositories/padron.py` — `VersionPadronRepository`, `EntradaPadronRepository`
- **Backend/services**: `backend/app/services/padron_service.py` — lógica de activación/desactivación, parsing de archivo, orquestación de Moodle WS
- **Backend/integrations**: `backend/app/integrations/moodle_ws.py` — cliente HTTP para Moodle Web Services
- **Backend/routers**: `backend/app/api/v1/routers/padron.py` registrado en `main.py`
- **Dependencias**: `openpyxl` (lectura xlsx), `httpx` (cliente Moodle WS async)
- **Auditoría**: acción `PADRON_CARGAR` en `audit_log`
- **Sin breaking changes** en APIs existentes
