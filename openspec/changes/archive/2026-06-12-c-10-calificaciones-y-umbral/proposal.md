## Why

El sistema necesita registrar el desempeño de los alumnos en actividades del LMS para que los docentes puedan detectar atrasados y generar reportes. Sin calificaciones no hay análisis posible — este es el núcleo del flujo central del PROFESOR (FL-02, pasos 3–4) y el prerequisito directo de C-11 (análisis y detección de atrasados).

## What Changes

- Modelos `Calificacion` y `UmbralMateria` con migración Alembic.
- Parser de archivo LMS: detecta columnas numéricas (terminan en `(Real)`, RN-01) y textuales (RN-02).
- Vista previa de actividades detectadas: el PROFESOR selecciona cuáles incluir antes de confirmar la importación.
- Import final: bulk-insert de `Calificacion` con derivación de `aprobado` en el momento de carga (numérica vs umbral, textual vs conjunto aprobatorio).
- Import de reporte de finalización (F1.2): detecta TPs entregados sin nota textual (RN-07, RN-08).
- Configuración de umbral por asignación (F2.1): endpoint `PUT /api/calificaciones/umbral` con valor por defecto 60 % (RN-03); el umbral es scope-isolated por asignación (RN-04).
- Vaciado scope-isolated de calificaciones por materia (F1.5, RN-04).
- Audit `CALIFICACIONES_IMPORTAR` en toda operación de escritura.

## Capabilities

### New Capabilities

- `calificaciones`: registro de notas de alumnos por materia y actividad, con derivación de `aprobado`; import desde archivo LMS con vista previa de actividades; configuración de umbral por asignación; vaciado scope-isolated.

### Modified Capabilities

*(ninguna — C-09 ya archivado, no hay specs existentes de calificaciones)*

## Impact

- **Nuevas tablas**: `calificacion`, `umbral_materia` (migration `007_calificaciones`).
- **Nuevos endpoints**: `POST /api/calificaciones/preview`, `POST /api/calificaciones/importar`, `POST /api/calificaciones/reporte-finalizacion`, `PUT /api/calificaciones/umbral`, `GET /api/calificaciones/umbral`, `DELETE /api/calificaciones` (vaciado).
- **Permiso RBAC**: `calificaciones:importar` (requerido en todos los endpoints de escritura).
- **Dependencias externas**: openpyxl (ya instalado desde C-09).
- **Impacto en C-11**: `calificacion.aprobado` es el campo central para análisis de atrasados y rankings.
