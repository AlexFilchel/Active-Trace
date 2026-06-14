## Why

El sistema ya cuenta con calificaciones y umbrales (C-10), pero aún no expone el análisis académico que permite detectar alumnos en riesgo y preparar el seguimiento del flujo central FL-02. C-11 convierte esos datos importados en reportes accionables para PROFESOR, TUTOR, COORDINADOR y ADMIN.

## What Changes

- Nueva capacidad de análisis bajo `/api/analisis/*`, protegida con `atrasados:ver`.
- Cómputo de alumnos atrasados por actividades faltantes o nota inferior al umbral (RN-06).
- Ranking de actividades aprobadas, excluyendo alumnos sin aprobadas (RN-09).
- Reportes rápidos por materia, notas finales agrupadas y monitores de seguimiento con filtros por rol.
- Export de TPs sin corregir basado en el cruce ya definido para entregas finalizadas sin calificación textual (RN-07/RN-08).
- Lógica de cálculo en Services; construcción SQL y filtros tenant-scope solo en Repositories.

## Capabilities

### New Capabilities

- `analisis-atrasados-reportes`: análisis de atrasados, rankings, reportes por materia, notas finales agrupadas, monitores y exports académicos basados en calificaciones y padrón.

### Modified Capabilities

*(ninguna — C-10 `calificaciones` queda como fuente de datos; no cambia sus requisitos archivados.)*

## Impact

- **API**: nuevos endpoints `GET /api/analisis/atrasados`, `GET /api/analisis/ranking-aprobadas`, `GET /api/analisis/materia/resumen`, `GET /api/analisis/notas-finales`, `GET /api/analisis/monitor`, `GET /api/analisis/tps-sin-corregir/export`.
- **Backend**: nuevo módulo de routers/schemas/services/repositories para `analisis`; DTOs Pydantic v2 con `extra='forbid'`.
- **Datos**: sin nuevas tablas previstas; consume `Calificacion`, `UmbralMateria`, `EntradaPadron`, `VersionPadron`, `Materia`, `Cohorte` y `Asignacion` existentes.
- **Seguridad**: identidad y tenant exclusivamente desde sesión JWT; permiso `atrasados:ver`; filtros por alcance docente/tutor/coordinación.
- **Pruebas**: definición de atrasado, ranking, notas finales, filtros de monitor, export e aislamiento tenant.

## Rollback Plan

Deshabilitar/remover rutas `/api/analisis/*` y el módulo `analisis` sin migraciones reversibles, porque no se agregan tablas ni se modifica persistencia existente.

## Dependencies

- C-10 `calificaciones-y-umbral` archivado.
- Specs principales `calificaciones`, `tenant-scoped-repositories`, `rbac` y `auth-identity-context`.

## Success Criteria

- [ ] Los endpoints retornan datos correctos y tenant-scoped con `atrasados:ver`.
- [ ] Las reglas RN-06, RN-07, RN-08 y RN-09 quedan cubiertas por tests RED→GREEN→TRIANGULATE→REFACTOR.
- [ ] Services no contienen SQL ni acceso directo a DB.
