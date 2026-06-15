# Tasks: C-24 — Frontend Finanzas y Admin

## FEATURE: FINANZAS

### Task 1.0 — Safety net baseline
- [ ] Run `npm run test -- --run` in `frontend/` and record passing count (expected: 134/134)

### Task 1.1 — Types for finanzas feature
- [ ] Create `frontend/src/features/finanzas/types/index.ts`
- [ ] Define: `Liquidacion`, `DetalleLiquidacion`, `LiquidacionKPIs`, `GrillaSalarial`, `Factura`, `EstadoFactura`, `Periodo`

### Task 1.2 — finanzasService (service layer)
- [ ] Create `frontend/src/features/finanzas/services/finanzasService.ts`
- [ ] Implement all C-18 endpoint wrappers using `apiClient`

### Task 1.3 — Hook: useLiquidaciones (RED → GREEN → TRIANGULATE → REFACTOR)
- [ ] Create `frontend/src/features/finanzas/hooks/useLiquidaciones.ts`
- [ ] Create `frontend/src/features/finanzas/hooks/hooks.test.tsx` — test case 1: fetches when periodo provided; test case 2: idle when no periodo

### Task 1.4 — Hook: useHistorialLiquidaciones
- [ ] Add to `useLiquidaciones.ts` or new file `useHistorialLiquidaciones.ts`
- [ ] Add tests: returns list; returns empty array

### Task 1.5 — Hook: useCerrarLiquidacion (mutation)
- [ ] Create `frontend/src/features/finanzas/hooks/useCerrarLiquidacion.ts`
- [ ] Add tests: mutation calls PUT; invalidates liquidaciones query on success

### Task 1.6 — Hooks: useGrillasSalariales + mutations
- [ ] Create `useGrillasSalariales.ts`, `useCrearGrilla.ts`, `useActualizarGrilla.ts`, `useEliminarGrilla.ts`
- [ ] Add tests: fetch returns list; create mutation posts; update mutation puts; delete mutation deletes

### Task 1.7 — Hooks: useFacturas + mutations
- [ ] Create `useFacturas.ts`, `useCrearFactura.ts`, `useActualizarEstadoFactura.ts`
- [ ] Add tests: fetch returns list; create posts; update estado puts

### Task 1.8 — Component: KPIsLiquidacion
- [ ] Create `frontend/src/features/finanzas/components/KPIsLiquidacion.tsx`
- [ ] Render total_docentes, total_honorarios, estado as summary cards
- [ ] Create `frontend/src/features/finanzas/components/components.test.tsx` — test renders KPIs data; test renders loading state

### Task 1.9 — Component: TablaDetalleLiquidacion
- [ ] Create `frontend/src/features/finanzas/components/TablaDetalleLiquidacion.tsx`
- [ ] Render segmented rows (filterable by segmento prop)
- [ ] Add tests: renders rows; renders empty state

### Task 1.10 — Component: HistorialLiquidaciones
- [ ] Create `frontend/src/features/finanzas/components/HistorialLiquidaciones.tsx`
- [ ] Render list of previous liquidaciones with fecha, periodo, estado, total
- [ ] Add tests: renders historial rows; renders empty state

### Task 1.11 — Component: GrillaSalarial + FormularioGrilla
- [ ] Create `frontend/src/features/finanzas/components/GrillaSalarial.tsx` — table with Edit/Delete per row
- [ ] Create `frontend/src/features/finanzas/components/FormularioGrilla.tsx` — Zod-validated form for categoria + salario_base
- [ ] Add tests: renders rows with edit/delete buttons; form validation blocks empty submit; form calls onSubmit with data

### Task 1.12 — Component: TablaFacturas + FormularioFactura
- [ ] Create `frontend/src/features/finanzas/components/TablaFacturas.tsx`
- [ ] Create `frontend/src/features/finanzas/components/FormularioFactura.tsx`
- [ ] Add tests: renders facturas; status change button calls mutation; form validates required fields

### Task 1.13 — Page: LiquidacionesPage
- [ ] Create `frontend/src/features/finanzas/pages/LiquidacionesPage.tsx`
- [ ] Tabs: "Liquidación Actual" (with KPIs + segmented detail + close button) | "Historial" | "Grilla Salarial" | "Facturas"
- [ ] Create `frontend/src/features/finanzas/pages/LiquidacionesPage.test.tsx`
- [ ] Tests: renders page title; tabs switch content; "Cerrar liquidación" button visible when liquidacion is ABIERTA

### Task 1.14 — Router: add /liquidaciones route
- [ ] Edit `frontend/src/router/index.tsx` — add lazy import + route for LiquidacionesPage under authenticated layout
- [ ] Add router test: `/liquidaciones` route renders LiquidacionesPage

---

## FEATURE: ADMIN

### Task 2.1 — Types for admin feature
- [ ] Create `frontend/src/features/admin/types/index.ts`
- [ ] Define: `Carrera`, `Cohorte`, `Materia`, `Usuario`, `Rol`, `AuditoriaEntry`, `AuditoriaFiltros`, `AuditoriaMetricas`, `PaginatedResponse<T>`

### Task 2.2 — adminService (service layer)
- [ ] Create `frontend/src/features/admin/services/adminService.ts`
- [ ] Implement C-06 (carreras/cohortes/materias), C-07 (usuarios), C-19 (auditoria/metricas) wrappers

### Task 2.3 — Hooks: useCarreras + mutations (RED → GREEN → TRIANGULATE → REFACTOR)
- [ ] Create `useCarreras.ts`, `useCrearCarrera.ts`, `useActualizarCarrera.ts`, `useEliminarCarrera.ts`
- [ ] Create `frontend/src/features/admin/hooks/hooks.test.tsx`
- [ ] Tests: fetches list; idle when skipped; create posts; update puts; delete deletes (invalidates on success)

### Task 2.4 — Hooks: useCohortes + mutations
- [ ] Create `useCohortes.ts`, `useCrearCohorte.ts`, `useActualizarCohorte.ts`, `useEliminarCohorte.ts`
- [ ] Add tests (same pattern as 2.3)

### Task 2.5 — Hooks: useMaterias + mutations
- [ ] Create `useMaterias.ts`, `useCrearMateria.ts`, `useActualizarMateria.ts`, `useEliminarMateria.ts`
- [ ] Add tests (same pattern as 2.3)

### Task 2.6 — Hooks: useUsuarios + mutations
- [ ] Create `useUsuarios.ts`, `useCrearUsuario.ts`, `useActualizarUsuario.ts`, `useAsignarRoles.ts`
- [ ] Add tests: fetches list; create posts; update puts; assign roles posts

### Task 2.7 — Hooks: useAuditoriaLog + useAuditoriaMetricas
- [ ] Create `useAuditoriaLog.ts` with params `(filtros: AuditoriaFiltros, page: number)`
- [ ] Create `useAuditoriaMetricas.ts`
- [ ] Add tests: log with no filters returns all; log with accion filter passes query param; metricas returns object

### Task 2.8 — Components: TablaCarreras + FormularioCarrera
- [ ] Create `frontend/src/features/admin/components/TablaCarreras.tsx`
- [ ] Create `frontend/src/features/admin/components/FormularioCarrera.tsx`
- [ ] Create `frontend/src/features/admin/components/components.test.tsx`
- [ ] Tests: renders rows; edit button opens form; form submits with name; form rejects empty name

### Task 2.9 — Components: TablaCohortes + FormularioCohorte
- [ ] Create `frontend/src/features/admin/components/TablaCohortes.tsx`
- [ ] Create `frontend/src/features/admin/components/FormularioCohorte.tsx`
- [ ] Add tests (same pattern as 2.8)

### Task 2.10 — Components: TablaMaterias + FormularioMateria
- [ ] Create `frontend/src/features/admin/components/TablaMaterias.tsx`
- [ ] Create `frontend/src/features/admin/components/FormularioMateria.tsx`
- [ ] Add tests (same pattern as 2.8)

### Task 2.11 — Components: TablaUsuarios + FormularioUsuario
- [ ] Create `frontend/src/features/admin/components/TablaUsuarios.tsx`
- [ ] Create `frontend/src/features/admin/components/FormularioUsuario.tsx`
- [ ] Add tests: renders users with role badge; form requires email/nombre; role assignment updates

### Task 2.12 — Components: FiltrosAuditoria + TablaLogAuditoria + MetricasAuditoria
- [ ] Create `frontend/src/features/admin/components/FiltrosAuditoria.tsx` — 5 filter fields (accion, usuario, desde, hasta, modulo)
- [ ] Create `frontend/src/features/admin/components/TablaLogAuditoria.tsx` — paginated table with prev/next controls
- [ ] Create `frontend/src/features/admin/components/MetricasAuditoria.tsx` — KPI cards
- [ ] Add tests: filtros onChange fired; tabla renders rows + pagination buttons; metricas renders values

### Task 2.13 — Page: AdminPage (tabs: Estructura / Usuarios / Auditoría)
- [ ] Create `frontend/src/features/admin/pages/AdminPage.tsx`
- [ ] 3 tabs with lazy sub-sections; each tab renders the corresponding components
- [ ] Create `frontend/src/features/admin/pages/AdminPage.test.tsx`
- [ ] Tests: renders page; tab "Usuarios" shows user table; tab "Auditoría" shows filtros + tabla

### Task 2.14 — Router: add /admin route
- [ ] Edit `frontend/src/router/index.tsx` — add lazy import + route for AdminPage under authenticated layout
- [ ] Add router test: `/admin` route renders AdminPage

---

## Validation

### Task 3.1 — Full test run
- [ ] Run `npm run test -- --run` in `frontend/` and verify ≥ 134 passing, 0 regressions
- [ ] Record final count in TDD evidence table

### Task 3.2 — LOC check
- [ ] Verify no component or service file exceeds 200 LOC
