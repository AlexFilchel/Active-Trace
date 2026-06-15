# Proposal: C-23 — Frontend Coordinación

## What

Implement the COORDINADOR/ADMIN frontend module within the existing React shell (C-21). This delivers six feature areas, each as a self-contained feature module under `frontend/src/features/`:

1. **equipos** — Gestión de equipos docentes (ABM, alta masiva, clonar, vigencia, export)
2. **avisos** — ABM de avisos con scope (comisión/cohorte/tenant) y acknowledgment tracking
3. **tareas** — Workflow de tareas internas (pendiente → en_progreso → completada), asignación, comentarios
4. **monitores** — Monitor general (F2.7) y monitor de entregas (F2.9)
5. **encuentros** — Gestión de encuentros y guardias
6. **coloquios** — Convocatorias, días con cupo, candidatos, reservas, resultados

## Why

All backend endpoints for C-08, C-13, C-14, C-15, C-16, C-17 are complete. COORDINADOR and ADMIN users have no frontend surface yet. This change delivers the complete coordination layer UI, giving those roles a full management experience.

## Scope

- **In scope**: 6 feature modules, router entries, nav links, MSW handlers, Vitest tests
- **Out of scope**: new backend endpoints, auth flows, alumno-facing views

## Dependencies

- C-21 ✅ — shell: router, layout, apiClient
- C-08 ✅ — equipos-docentes backend
- C-13 ✅ — encuentros-y-guardias backend  
- C-14 ✅ — evaluaciones-y-coloquios backend
- C-15 ✅ — avisos-y-acknowledgment backend
- C-16 ✅ — tareas-internas backend
- C-17 ✅ — programas-y-fechas-academicas backend

## Governance

**LOW** — Frontend CRUD pages with no auth/tenancy logic. Backend already enforces all rules. Full autonomy if tests pass.

## Success Criteria

1. All 6 feature modules render their main list views
2. Forms submit with correct payloads (validated via MSW handlers)
3. Workflow transitions (tarea states) work
4. Tests ≥ 134 (baseline) + new tests — all passing
5. No TypeScript errors (`any` banned), components < 200 LOC
