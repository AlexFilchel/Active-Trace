# Design: C-24 — Frontend Finanzas y Admin

## Architecture

Following the identical pattern established in C-22 (`features/comisiones/`):

```
frontend/src/features/
  finanzas/
    types/          index.ts  — all TS types for the feature
    services/       finanzasService.ts — apiClient wrappers
    hooks/          useLiquidaciones.ts, useHistorialLiquidaciones.ts,
                    useCerrarLiquidacion.ts, useGrillasSalariales.ts,
                    useCrearGrilla.ts, useActualizarGrilla.ts,
                    useEliminarGrilla.ts, useFacturas.ts,
                    useCrearFactura.ts, useActualizarEstadoFactura.ts
    components/     PanelLiquidacion.tsx, KPIsLiquidacion.tsx,
                    TablaDetalleLiquidacion.tsx, HistorialLiquidaciones.tsx,
                    GrillaSalarial.tsx, FormularioGrilla.tsx,
                    TablaFacturas.tsx, FormularioFactura.tsx
    pages/          LiquidacionesPage.tsx

  admin/
    types/          index.ts  — types for carreras, cohortes, materias, usuarios, auditoria
    services/       adminService.ts — apiClient wrappers
    hooks/          useCarreras.ts, useCohortes.ts, useMaterias.ts,
                    useUsuarios.ts, useAuditoriaLog.ts, useAuditoriaMetricas.ts,
                    useCrearCarrera.ts, useActualizarCarrera.ts, useEliminarCarrera.ts,
                    useCrearCohorte.ts, useActualizarCohorte.ts, useEliminarCohorte.ts,
                    useCrearMateria.ts, useActualizarMateria.ts, useEliminarMateria.ts,
                    useCrearUsuario.ts, useActualizarUsuario.ts, useAsignarRoles.ts
    components/     TablaCarreras.tsx, FormularioCarrera.tsx,
                    TablaCohortes.tsx, FormularioCohorte.tsx,
                    TablaMaterias.tsx, FormularioMateria.tsx,
                    TablaUsuarios.tsx, FormularioUsuario.tsx,
                    PanelAuditoria.tsx, FiltrosAuditoria.tsx, TablaLogAuditoria.tsx,
                    MetricasAuditoria.tsx
    pages/          AdminPage.tsx (tabs: Estructura / Usuarios / Auditoría)
```

## Key Design Decisions

### DD-1: Single service per feature (not per API domain)
`finanzasService` wraps all C-18 endpoints. `adminService` wraps C-06, C-07 and C-19 endpoints. Same pattern as `comisionesService` — one import, minimal coupling.

### DD-2: AdminPage uses tabs (not sub-routes)
Admin has 3 sections (Estructura / Usuarios / Auditoría). Using client-side tabs (state) instead of nested routes keeps the router flat and avoids the `<Outlet>` boilerplate that adds zero value here. If a deep-link is needed later, the tab can be made a query param.

### DD-3: LiquidacionesPage uses segmented tabs matching the API's segmentation
The backend distinguishes "general / NEXO / factura" in the detail endpoint. The page renders three tabs: `General`, `NEXO`, `Facturas`. The KPI summary bar is always visible above the tabs.

### DD-4: Pagination for audit log is managed locally in `useAuditoriaLog`
`page` and `page_size` are state inside the hook, exposed via returned setters. The component calls `setPage(n)`. No URL query params needed for this internal admin tool.

### DD-5: Forms use React Hook Form + Zod v4 (same as auth forms in C-21)
All create/edit forms validate client-side before calling the mutation hook.

### DD-6: MSW handlers in test files (not in server.ts)
Handlers registered with `server.use(...)` inside `beforeEach` of each test suite, reset via `afterEach(() => server.resetHandlers())`. Matches the exact pattern in `hooks.test.tsx` of comisiones.

## Router Changes

`frontend/src/router/index.tsx` — add lazy-loaded pages:

```tsx
const LiquidacionesPage = lazy(() => import('@/features/finanzas/pages/LiquidacionesPage').then(...))
const AdminPage         = lazy(() => import('@/features/admin/pages/AdminPage').then(...))
```

Routes added under the authenticated layout:
```
/liquidaciones  → LiquidacionesPage
/admin          → AdminPage
```

## Nav (AuthenticatedLayout.tsx)

The nav already has the entries:
```ts
{ label: 'Liquidaciones', path: '/liquidaciones', roles: ['FINANZAS', 'ADMIN'] },
{ label: 'Administración', path: '/admin',          roles: ['ADMIN'] },
```
No changes needed to `AuthenticatedLayout.tsx`.

## Testing Strategy

- **Hook tests**: `renderHook` + `QueryClientProvider` + MSW. Two test cases per hook (happy path + edge/triangulate).
- **Component tests**: `render` + user events (RTL `userEvent`) + MSW. Test renders, interactions (click, form submit), and error states.
- **Page tests**: Smoke render + tab navigation + role-gated rendering.
- All tests in colocated `*.test.tsx` files.

## LOC Budget

| File | Estimated LOC | Note |
|------|--------------|------|
| finanzasService.ts | ~120 | All C-18 wrappers |
| adminService.ts | ~130 | C-06 + C-07 + C-19 wrappers |
| LiquidacionesPage.tsx | ~160 | Split tabs |
| AdminPage.tsx | ~180 | 3 tabs with lazy sub-sections |
| PanelLiquidacion.tsx | ~80 | KPIs + action buttons |
| TablaLogAuditoria.tsx | ~120 | Paginated table |
| FiltrosAuditoria.tsx | ~100 | Form with 5 filter fields |
| GrillaSalarial.tsx + FormularioGrilla.tsx | ~130+90 | ABM table + modal form |
| TablaUsuarios.tsx + FormularioUsuario.tsx | ~100+120 | User list + role form |
| All hook files | ~15–25 each | Thin TanStack Query wrappers |
