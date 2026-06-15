# Tasks: C-23 — Frontend Coordinación

## T-01 — Shared MSW handlers + types infrastructure
- [ ] Add MSW handlers for all 6 feature endpoints in `frontend/src/test/server.ts`

## T-02 — Feature: equipos
- [ ] `frontend/src/features/equipos/types/index.ts` — Equipo, MiembroEquipo, EquipoCreate types
- [ ] `frontend/src/features/equipos/services/equiposService.ts` — 9 API methods
- [ ] `frontend/src/features/equipos/services/equiposService.test.ts` — service tests (TDD)
- [ ] `frontend/src/features/equipos/hooks/useEquipos.ts` — list query hook
- [ ] `frontend/src/features/equipos/hooks/useCreateEquipo.ts` — mutation hook
- [ ] `frontend/src/features/equipos/hooks/useDeleteEquipo.ts` — mutation hook
- [ ] `frontend/src/features/equipos/hooks/useClonarEquipo.ts` — mutation hook
- [ ] `frontend/src/features/equipos/hooks/hooks.test.tsx` — hook tests (TDD)
- [ ] `frontend/src/features/equipos/components/TablaEquipos.tsx` — list component
- [ ] `frontend/src/features/equipos/components/FormEquipo.tsx` — create/edit form
- [ ] `frontend/src/features/equipos/pages/EquiposPage.tsx` — orchestrator page
- [ ] `frontend/src/features/equipos/pages/EquiposPage.test.tsx` — page smoke test

## T-03 — Feature: avisos
- [ ] `frontend/src/features/avisos/types/index.ts` — Aviso, AvisoScope, Acknowledgment types
- [ ] `frontend/src/features/avisos/services/avisosService.ts` — 5 API methods
- [ ] `frontend/src/features/avisos/services/avisosService.test.ts` — service tests (TDD)
- [ ] `frontend/src/features/avisos/hooks/useAvisos.ts` — list query hook
- [ ] `frontend/src/features/avisos/hooks/useCreateAviso.ts` — mutation hook
- [ ] `frontend/src/features/avisos/hooks/useDeleteAviso.ts` — mutation hook
- [ ] `frontend/src/features/avisos/hooks/hooks.test.tsx` — hook tests (TDD)
- [ ] `frontend/src/features/avisos/components/TablaAvisos.tsx` — list component
- [ ] `frontend/src/features/avisos/components/FormAviso.tsx` — create form
- [ ] `frontend/src/features/avisos/pages/AvisosPage.tsx` — orchestrator page
- [ ] `frontend/src/features/avisos/pages/AvisosPage.test.tsx` — page smoke test

## T-04 — Feature: tareas
- [ ] `frontend/src/features/tareas/types/index.ts` — Tarea, TareaEstado, Comentario types
- [ ] `frontend/src/features/tareas/services/tareasService.ts` — 6 API methods
- [ ] `frontend/src/features/tareas/services/tareasService.test.ts` — service tests (TDD)
- [ ] `frontend/src/features/tareas/hooks/useTareas.ts` — list query hook
- [ ] `frontend/src/features/tareas/hooks/useCreateTarea.ts` — mutation hook
- [ ] `frontend/src/features/tareas/hooks/useUpdateTarea.ts` — mutation hook (workflow)
- [ ] `frontend/src/features/tareas/hooks/hooks.test.tsx` — hook tests (TDD)
- [ ] `frontend/src/features/tareas/components/TarjetaTarea.tsx` — single task card
- [ ] `frontend/src/features/tareas/components/KanbanTareas.tsx` — kanban board
- [ ] `frontend/src/features/tareas/components/FormTarea.tsx` — create form
- [ ] `frontend/src/features/tareas/pages/TareasPage.tsx` — orchestrator page
- [ ] `frontend/src/features/tareas/pages/TareasPage.test.tsx` — page smoke test

## T-05 — Feature: monitores
- [ ] `frontend/src/features/monitores/types/index.ts` — MonitorItem, EntregaMonitor types
- [ ] `frontend/src/features/monitores/services/monitoresService.ts` — 2 API methods
- [ ] `frontend/src/features/monitores/services/monitoresService.test.ts` — service tests (TDD)
- [ ] `frontend/src/features/monitores/hooks/useMonitorGeneral.ts` — query hook
- [ ] `frontend/src/features/monitores/hooks/useMonitorEntregas.ts` — query hook
- [ ] `frontend/src/features/monitores/hooks/hooks.test.tsx` — hook tests (TDD)
- [ ] `frontend/src/features/monitores/components/TablaMonitor.tsx` — general monitor table
- [ ] `frontend/src/features/monitores/components/TablaEntregasMonitor.tsx` — entregas table
- [ ] `frontend/src/features/monitores/pages/MonitoresPage.tsx` — orchestrator page
- [ ] `frontend/src/features/monitores/pages/MonitoresPage.test.tsx` — page smoke test

## T-06 — Feature: encuentros
- [ ] `frontend/src/features/encuentros/types/index.ts` — Encuentro, Guardia types
- [ ] `frontend/src/features/encuentros/services/encuentrosService.ts` — 6 API methods
- [ ] `frontend/src/features/encuentros/services/encuentrosService.test.ts` — service tests (TDD)
- [ ] `frontend/src/features/encuentros/hooks/useEncuentros.ts` — list query hook
- [ ] `frontend/src/features/encuentros/hooks/useCreateEncuentro.ts` — mutation hook
- [ ] `frontend/src/features/encuentros/hooks/useGuardias.ts` — list query hook
- [ ] `frontend/src/features/encuentros/hooks/hooks.test.tsx` — hook tests (TDD)
- [ ] `frontend/src/features/encuentros/components/TablaEncuentros.tsx` — list component
- [ ] `frontend/src/features/encuentros/components/FormEncuentro.tsx` — create form
- [ ] `frontend/src/features/encuentros/pages/EncuentrosPage.tsx` — orchestrator page
- [ ] `frontend/src/features/encuentros/pages/EncuentrosPage.test.tsx` — page smoke test

## T-07 — Feature: coloquios
- [ ] `frontend/src/features/coloquios/types/index.ts` — Coloquio, ColoquioDia, Candidato types
- [ ] `frontend/src/features/coloquios/services/coloquiosService.ts` — 8 API methods
- [ ] `frontend/src/features/coloquios/services/coloquiosService.test.ts` — service tests (TDD)
- [ ] `frontend/src/features/coloquios/hooks/useColoquios.ts` — list query hook
- [ ] `frontend/src/features/coloquios/hooks/useCreateColoquio.ts` — mutation hook
- [ ] `frontend/src/features/coloquios/hooks/useColoquioDias.ts` — query hook
- [ ] `frontend/src/features/coloquios/hooks/useColoquioCandidatos.ts` — query hook
- [ ] `frontend/src/features/coloquios/hooks/hooks.test.tsx` — hook tests (TDD)
- [ ] `frontend/src/features/coloquios/components/TablaColoquios.tsx` — list component
- [ ] `frontend/src/features/coloquios/components/FormColoquio.tsx` — create form
- [ ] `frontend/src/features/coloquios/components/DetallColoquio.tsx` — detail with tabs
- [ ] `frontend/src/features/coloquios/pages/ColoquiosPage.tsx` — orchestrator page
- [ ] `frontend/src/features/coloquios/pages/ColoquiosPage.test.tsx` — page smoke test

## T-08 — Router + nav wiring
- [ ] Add 6 route entries to `frontend/src/router/index.tsx`
- [ ] Add 6 nav entries to `frontend/src/shared/components/AuthenticatedLayout.tsx`
