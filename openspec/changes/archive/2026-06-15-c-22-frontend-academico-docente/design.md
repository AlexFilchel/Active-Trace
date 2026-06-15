## Context

El shell autenticado (C-21) ya provee: router con `createBrowserRouter`/`createMemoryRouter`, `AuthenticatedLayout` con nav por roles, `RequireAuth`, sesión (`useSession`), y un `apiClient` Axios centralizado (`@/shared/services/api`) con refresh transparente en 401 y propagación de 403. El backend (C-10/C-11/C-12) expone todos los endpoints de calificaciones, análisis y comunicaciones. El testing usa Vitest + RTL + MSW con un `server` compartido (`@/test/server`) y `onUnhandledRequest: 'error'`; los tests interceptan sobre `http://localhost:8000`.

Esta feature es de capa de presentación (governance BAJO): consume contratos ya definidos, no toca dominio crítico. La identidad/tenant/roles viajan en el JWT que `apiClient` inyecta — el frontend nunca los pasa como parámetro.

## Goals / Non-Goals

**Goals:**

- Entregar el flujo FL-02 completo para PROFESOR dentro del shell existente: seleccionar comisión → importar calificaciones → configurar umbral → analizar → comunicar y trackear.
- Estructura feature-based aislada en `src/features/comisiones/` reutilizable y testeable.
- Toda I/O de red pasa por servicios de la feature que usan `apiClient`; todo fetch pasa por hooks de TanStack Query.
- Tests con MSW (nunca mock de Axios), siguiendo Strict TDD.

**Non-Goals:**

- Vistas de COORDINADOR/ADMIN (monitor general transversal F2.7/F2.9, aprobación de envíos F3.3) — quedan fuera; esta feature es PROFESOR.
- Aprobación de envíos masivos (FL-04 parte B) — pertenece al rol aprobador, otro change.
- Modificar contratos de backend o el shell (router/layout solo se extienden, no se reescriben).
- Mensajería interna (F3.4 / inbox) — change separado.

## Decisions

### D1 — Estructura de la feature

`src/features/comisiones/{types,services,hooks,components,pages}`. Una sola feature `comisiones` agrupa las tres capabilities (importacion, analisis, comunicacion) porque comparten el contexto de `comision_id` y la misma página contenedora con pestañas. Alternativa descartada: tres features separadas → fragmentaría el estado de comisión seleccionada y duplicaría la página contenedora.

### D2 — Estado de la comisión seleccionada

`comision_id` vive en estado local de la página contenedora (`ComisionesPage`) y se pasa por props a los componentes hijos / como argumento a los hooks. Alternativa descartada: Context global → innecesario, el scope es una sola página; agregaría complejidad sin beneficio (no hay consumidores lejanos).

### D3 — Capa de servicios

Un objeto `comisionesService` (patrón `authService`) con métodos async tipados que llaman a `apiClient` y devuelven `res.data`. Sin `any`; tipos en `types/index.ts`. La importación usa `FormData` (multipart) con header `multipart/form-data` por petición (override del default JSON del `apiClient`).

### D4 — Hooks TanStack Query v5

- Lecturas (`actividades`, `umbral`, `atrasados`, `ranking`, `notas-finales`, `reporte-rapido`, `entregas-sin-corregir`, `estado`) → `useQuery` con `queryKey` que incluye `comision_id`; `enabled: !!comisionId` para no disparar sin comisión.
- Escrituras (`importar`, `actualizar umbral`, `preview`, `enviar`) → `useMutation`; tras `importar`/`enviar` se invalidan las queries afectadas.
- **Tracking en tiempo real**: `useComunicacionesEstado` usa `refetchInterval` (polling) — el backend expone `GET /api/comunicaciones/estado`, no hay WebSocket. Alternativa descartada: SSE/WS → no soportado por el backend actual; polling con intervalo es suficiente para reflejar Pendiente→Enviando→OK/Fallido/Cancelado.

### D5 — Forms y validación

React Hook Form + Zod (patrón `LoginPage`): umbral (0–100), selección de actividades (al menos una para importar), mensaje personalizado opcional. `zodResolver` para validación tipada.

### D6 — Componentes < 200 LOC

Cada vista es un componente chico: `ImportadorCalificaciones`, `ConfiguradorUmbral`, `TablaAtrasados`, `TablaRanking`, `TablaNotasFinales`, `ReporteRapido`, `TablaEntregasSinCorregir`, `MonitorSeguimiento`, `PreviewComunicacion`, `PanelEstadoComunicaciones`. La `ComisionesPage` orquesta con pestañas y queda delgada. Estados informativos (sin datos / sin comisión) son componentes/ramas reutilizables.

### D7 — Routing y navegación

`/comisiones` (lazy + Suspense) como ruta hija de `AuthenticatedLayout` en `src/router/index.tsx`, reemplazando el catch-all `*` para esa ruta. En `AuthenticatedLayout.tsx` el nav item "Comisiones" agrega `PROFESOR` a sus roles visibles.

### D8 — Exportación de archivos

Para "entregas sin corregir" y otras exportaciones, el endpoint devuelve datos descargables; el frontend genera la descarga creando un `Blob` y un enlace temporal (sin dependencia nueva). En tests se verifica que se invoca la generación de descarga, no el efecto del navegador.

### D9 — Estrategia de testing (Strict TDD)

- Servicios: test que afirma método llama al endpoint correcto con el payload correcto (MSW intercepta y captura request).
- Hooks: `renderHook` + `QueryClientProvider` (wrapper con `retry: false`), MSW para respuestas y errores; triangulación (éxito + vacío + error).
- Componentes: RTL `render` con `QueryClientProvider`, MSW; afirmar render de datos, estados informativos, validaciones y disparo de mutaciones.
- Tracking: usar `refetchInterval` y `waitFor` para verificar transición de estado tras cambiar el handler de MSW.

## Risks / Trade-offs

- [Polling de estado genera carga periódica] → `refetchInterval` moderado y `enabled` solo cuando el panel de tracking está montado y hay comisión seleccionada.
- [Contratos de respuesta de C-10/C-11/C-12 no verificados campo a campo desde el frontend] → los tipos en `types/` se derivan de la KB y los endpoints listados; al implementar cada task se ajustan contra la respuesta real. Mitigación: mantener los tipos estrechos y fallar temprano en tests si el shape no coincide.
- [Multipart override del `apiClient` JSON-por-default] → pasar `headers` por petición en el método de importación; cubierto por test del servicio.
- [El monitor de seguimiento (F2.8) puede solaparse con la vista de atrasados] → se mantiene como vista filtrable distinta (filtros por alumno y mínimo cumplido) y se delimita su alcance a la comisión seleccionada.

## Migration Plan

Feature aditiva, sin migración de datos. Despliegue: incluir la feature en el bundle del frontend. Rollback: revertir las rutas en `router/index.tsx` y el rol en `AuthenticatedLayout.tsx` deja la sección "Próximamente"; no hay estado persistido nuevo.

## Open Questions

- Shape exacto de cada respuesta (campos de `atrasados`, `ranking`, `reporte-rapido`, `estado`): se confirma contra el backend al implementar cada hook; los tests con MSW fijan el contrato esperado y se ajustan si difiere.
- Formato de archivo de exportación de "entregas sin corregir" (CSV vs xlsx): se resuelve al inspeccionar el `Content-Type`/payload real del endpoint en la task correspondiente.
