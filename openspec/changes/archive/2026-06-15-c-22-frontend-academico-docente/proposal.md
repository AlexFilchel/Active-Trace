## Why

El rol PROFESOR es el de mayor uso del sistema (flujo central FL-02), pero hoy el frontend solo tiene el shell autenticado (C-21): el item de navegación "Comisiones" existe pero apunta a una sección "Próximamente". El backend ya expone todos los endpoints de calificaciones (C-10), análisis/atrasados (C-11) y comunicaciones-cola (C-12), de modo que el valor de negocio ya construido no es accesible para el docente. Esta feature cierra ese gap entregando el flujo extremo a extremo "importar → analizar → comunicar" sobre una comisión.

## What Changes

- Se incorpora la feature `comisiones` bajo `src/features/comisiones/` (estructura feature-based: `components`, `hooks`, `services`, `types`, `pages`).
- **Selección de comisión**: el PROFESOR elige la materia/comisión a gestionar; todas las vistas se acotan a esa comisión.
- **Importación de calificaciones** (F1.1, FL-02 pasos 3–4): listado de actividades detectadas (`GET /api/calificaciones/actividades`), selección de actividades a incluir, carga del archivo del LMS (`POST /api/calificaciones/importar`, multipart) con vista previa.
- **Configuración de umbral** (F2.1, RN-03): leer y actualizar el umbral de aprobación por comisión (`GET`/`PUT /api/calificaciones/umbral`), default 60%.
- **Vistas de análisis** (Épica 2, FL-02 paso 5): alumnos atrasados (`GET /api/atrasados`), ranking de actividades aprobadas (`GET /api/analisis/ranking`), notas finales agrupadas (`GET /api/calificaciones/notas-finales`) y reporte rápido por comisión (`GET /api/analisis/reporte-rapido`), con estados informativos cuando no hay datos.
- **Entregas sin corregir** (F2.6, FL-02 paso 6): tabla de posibles entregas pendientes (`GET /api/analisis/entregas-sin-corregir`) con exportación a archivo descargable.
- **Comunicación a atrasados** (Épica 3, FL-02 paso 7, FL-04): vista previa del mensaje (`POST /api/comunicaciones/preview`), envío masivo (`POST /api/comunicaciones/enviar`) y tracking del estado de la cola en tiempo real (`GET /api/comunicaciones/estado`, con refetch periódico) mostrando Pendiente → Enviando → OK / Fallido / Cancelado.
- **Monitor de seguimiento** (F2.8): vista filtrable del estado de actividades de la comisión para tutor/profesor.
- Se registran las rutas de la feature en `src/router/index.tsx` (lazy + Suspense) bajo `/comisiones`.
- El item de navegación "Comisiones" en `AuthenticatedLayout.tsx` se hace visible al rol PROFESOR (hoy restringido a COORDINADOR/ADMIN).
- Tests de componentes y hooks con Vitest + RTL + MSW (sin mockear Axios): import flow, tabla de atrasados, preview de comunicación, tracking de estados.

## Capabilities

### New Capabilities

- `frontend-comisiones-importacion`: UI de selección de comisión, listado/selección de actividades, importación de calificaciones con vista previa y configuración de umbral de aprobación.
- `frontend-comisiones-analisis`: vistas de atrasados, ranking, notas finales, reporte rápido y entregas sin corregir con exportación, más el monitor de seguimiento de la comisión.
- `frontend-comisiones-comunicacion`: vista previa, envío masivo y tracking en tiempo real del estado de la cola de comunicaciones a alumnos atrasados.

### Modified Capabilities

<!-- Ninguna: no existen specs previas cuyos requisitos cambien. El shell (C-21) provee router/layout/HTTP client que se consumen sin modificar su contrato. -->

## Impact

- **Código nuevo**: `frontend/src/features/comisiones/` (services, hooks, types, components, pages).
- **Código modificado**: `frontend/src/router/index.tsx` (rutas `/comisiones/*`), `frontend/src/shared/components/AuthenticatedLayout.tsx` (rol PROFESOR en nav).
- **Backend**: consumo (no modificación) de endpoints C-10, C-11, C-12. Contratos de request/response ya definidos.
- **Dependencias**: usa el `apiClient` de `@/shared/services/api` (no `fetch`), TanStack Query v5, React Hook Form + Zod, Tailwind v4. Sin nuevas dependencias de runtime.
- **Tests**: nuevos archivos `*.test.tsx`/`*.test.ts` con MSW sobre `http://localhost:8000`, usando el `server` compartido de `@/test/server`.
- **Governance**: BAJO — feature de presentación que consume contratos existentes; autonomía total con tests verdes.
