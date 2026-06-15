# Tareas — c-22-frontend-academico-docente

> Strict TDD: cada task de código sigue RED (test que falla) → GREEN (mínimo) → TRIANGULATE (2+ casos) → REFACTOR.
> Todo fetch via `apiClient` (`@/shared/services/api`). Tests con Vitest + RTL + MSW (`@/test/server`), nunca mock de Axios.
> Componentes < 200 LOC, PascalCase; hooks/services camelCase; sin `any`; Tailwind only.

## 1. Andamiaje de la feature

- [x] 1.1 Crear estructura `src/features/comisiones/{types,services,hooks,components,pages}` con `index.ts` donde corresponda
- [x] 1.2 Definir tipos en `types/index.ts`: `Comision`, `Actividad`, `UmbralConfig`, `AlumnoAtrasado`, `RankingItem`, `NotaFinal`, `ReporteRapido`, `EntregaSinCorregir`, `ComunicacionPreview`, `EstadoComunicacion` (enum Pendiente/Enviando/OK/Fallido/Cancelado), `EstadoDestinatario`

## 2. Servicio de comisiones (TDD: test del request por endpoint)

- [x] 2.1 `services/comisionesService.ts` — `getActividades(comisionId, tipo?)` → `GET /api/calificaciones/actividades` (test MSW captura query)
- [x] 2.2 `importarCalificaciones(comisionId, file, actividades)` → `POST /api/calificaciones/importar` multipart con `FormData` y header `multipart/form-data` (test verifica payload + override de header)
- [x] 2.3 `getUmbral(comisionId)` + `putUmbral(comisionId, umbralPct, valoresAprobatorios)` → `GET`/`PUT /api/calificaciones/umbral`
- [x] 2.4 `getAtrasados`, `getRanking`, `getNotasFinales`, `getReporteRapido`, `getEntregasSinCorregir` → endpoints C-11/C-10 (test por método)
- [x] 2.5 `previewComunicacion(comisionId, tipo)`, `enviarComunicacion(comisionId, tipo, mensajePersonalizado?)`, `getEstadoComunicaciones(comisionId)` → endpoints C-12

## 3. Hooks de lectura (TanStack Query)

- [x] 3.1 `hooks/useActividades.ts` — `useQuery` con `enabled: !!comisionId`; triangular: lista con datos, lista vacía, error
- [x] 3.2 `hooks/useUmbral.ts` — query del umbral; default 60% cuando no hay configuración; triangular
- [x] 3.3 `hooks/useAtrasados.ts` — query; triangular (datos / vacío / error)
- [x] 3.4 `hooks/useRanking.ts` y `hooks/useNotasFinales.ts` — queries; triangular
- [x] 3.5 `hooks/useReporteRapido.ts` y `hooks/useEntregasSinCorregir.ts` — queries; triangular (incluye estado "sin datos")
- [x] 3.6 `hooks/useComunicacionesEstado.ts` — query con `refetchInterval`; test verifica refresco que refleja transición Pendiente→OK al cambiar handler MSW

## 4. Hooks de mutación

- [x] 4.1 `hooks/useImportarCalificaciones.ts` — `useMutation`; invalida queries de análisis al éxito; triangular (éxito / error)
- [x] 4.2 `hooks/useActualizarUmbral.ts` — `useMutation`; refleja nuevo valor; triangular
- [x] 4.3 `hooks/usePreviewComunicacion.ts` — `useMutation`; expone preview; triangular (éxito / error)
- [x] 4.4 `hooks/useEnviarComunicacion.ts` — `useMutation`; refresca estado de cola al éxito; triangular

## 5. Importación y umbral (componentes)

- [x] 5.1 `components/SelectorActividades.tsx` — lista actividades con selección; estado "sin actividades"; (RED: render con datos, render vacío)
- [x] 5.2 `components/ImportadorCalificaciones.tsx` — carga de archivo + selección + confirmar; bloquea sin actividad seleccionada; muestra vista previa al éxito y error al fallo (triangular los 3 escenarios del spec)
- [x] 5.3 `components/ConfiguradorUmbral.tsx` — RHF+Zod (0–100); muestra umbral vigente; envía PUT; valida fuera de rango (triangular: muestra 70%, actualiza a 65%, bloquea fuera de rango)

## 6. Vistas de análisis (componentes)

- [x] 6.1 `components/TablaAtrasados.tsx` — render de atrasados con motivo; estado "sin alumnos atrasados" (triangular)
- [x] 6.2 `components/TablaRanking.tsx` — render ordenado desc; estado vacío (triangular)
- [x] 6.3 `components/TablaNotasFinales.tsx` — render de notas finales
- [x] 6.4 `components/ReporteRapido.tsx` — métricas con datos; estado informativo sin datos (triangular)
- [x] 6.5 `components/TablaEntregasSinCorregir.tsx` — render por alumno/actividad; estado vacío deshabilita exportar (triangular)
- [x] 6.6 `components/ExportarEntregas` — utilidad/acción de descarga vía `Blob` + enlace temporal; test verifica que se invoca la generación de descarga con entregas presentes
- [x] 6.7 `components/MonitorSeguimiento.tsx` — vista filtrable por alumno y mínimo de actividades cumplidas (triangular: filtro por alumno, filtro por mínimo)

## 7. Comunicación (componentes)

- [x] 7.1 `components/PreviewComunicacion.tsx` — muestra asunto+cuerpo; error deshabilita envío (triangular: muestra preview, error)
- [x] 7.2 `components/PanelEnvioComunicacion` — confirmar envío tras preview; botón deshabilitado sin preview; incluye `mensaje_personalizado` opcional (triangular: envío confirmado, con mensaje personalizado, bloqueado sin preview)
- [x] 7.3 `components/PanelEstadoComunicaciones.tsx` — tracking con estados por destinatario; refresco refleja transición; estado "sin comunicaciones" (triangular: muestra estados, refresco Pendiente→OK, vacío)

## 8. Página contenedora y wiring

- [x] 8.1 `pages/ComisionesPage.tsx` — selector de comisión + estado de comisión seleccionada; estado informativo cuando no hay comisión seleccionada; pestañas Importación / Análisis / Comunicación que orquestan los componentes (mantener < 200 LOC, delgada)
- [x] 8.2 Registrar ruta `/comisiones` (lazy + Suspense) como hija de `AuthenticatedLayout` en `src/router/index.tsx`; test con `createMemoryRouter` verifica que `/comisiones` renderiza la página
- [x] 8.3 Agregar `PROFESOR` a los roles visibles del nav item "Comisiones" en `src/shared/components/AuthenticatedLayout.tsx`; test verifica visibilidad para PROFESOR

## 9. Cierre

- [x] 9.1 Verificar suite de la feature en verde (Vitest) y ausencia de `any`/handlers MSW no usados
- [ ] 9.2 Marcar `[x]` en CHANGES.md para C-22 y dejar registro en engram
