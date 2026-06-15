# Proposal: C-24 — Frontend Finanzas y Admin

## What

Add two role-gated feature modules to the React SPA:

**Feature FINANZAS** (roles: `FINANZAS`, `ADMIN`)
- Vista de liquidaciones del período con segmentación (general / NEXO / factura) + KPIs
- Acción de cerrar liquidación del período
- Historial de liquidaciones anteriores
- Grilla salarial: ABM de salarios base por categoría
- Gestión de facturas: listar, registrar, aprobar/rechazar

**Feature ADMIN** (role: `ADMIN`)
- Estructura académica: gestión de carreras, cohortes, materias (CRUD)
- Usuarios del tenant: listado, asignación de roles, activar/desactivar
- Panel de auditoría y métricas: log completo con filtros (acción, usuario, fecha, módulo) + métricas

## Why

C-18 (liquidaciones-y-honorarios) y C-19 (panel-auditoria-metricas) implementaron la API backend completa. C-21 provee el shell (router, AuthenticatedLayout, apiClient). Sin esta feature, el rol FINANZAS no puede operar el módulo financiero y el ADMIN no puede gestionar estructura ni auditar el sistema desde el frontend.

## Dependencies (all complete)
- C-21 ✅ — shell: router, layout, apiClient
- C-18 ✅ — liquidaciones-y-honorarios backend
- C-19 ✅ — panel-auditoria-metricas backend
- C-06 ✅ — estructura-academica backend
- C-07 ✅ — usuarios backend

## Scope

### In scope
- `frontend/src/features/finanzas/` — tipos, servicio, hooks, componentes, página
- `frontend/src/features/admin/` — tipos, servicio, hooks, componentes, páginas
- `frontend/src/router/index.tsx` — agregar rutas `/liquidaciones`, `/admin/*`
- `frontend/src/shared/components/AuthenticatedLayout.tsx` — nav entries ya presentes (Liquidaciones, Administración)
- `frontend/src/test/server.ts` — extender con handlers MSW para las nuevas rutas
- Tests Vitest + RTL + MSW para cada hook y componente crítico

### Out of scope
- Notificaciones en tiempo real (WebSocket)
- Exportación a PDF/Excel
- Wizard de onboarding de tenant (C-08)

## Constraints
- Governance: BAJO — CRUD e interfaz de reporting; no toca auth ni multi-tenancy
- Baseline test: 134/134 passing — no regresiones permitidas
- React 19 + TypeScript strict, Tailwind v4, TanStack Query v5, React Hook Form + Zod v4
- Components < 200 LOC; split si superan
- Strict TDD: test RED → GREEN → TRIANGULATE → REFACTOR por cada tarea

## Key Backend Endpoints

### C-18 — Liquidaciones y honorarios
- `GET  /api/liquidaciones?periodo=`
- `POST /api/liquidaciones/calcular`
- `PUT  /api/liquidaciones/{id}/cerrar`
- `GET  /api/liquidaciones/{id}/detalle`
- `GET  /api/liquidaciones/historial`
- `GET  /api/salarios/grilla`
- `POST /api/salarios/grilla`
- `PUT  /api/salarios/grilla/{id}`
- `DELETE /api/salarios/grilla/{id}`
- `GET  /api/facturas`
- `POST /api/facturas`
- `PUT  /api/facturas/{id}/estado`

### C-19 — Auditoría y métricas
- `GET /api/auditoria/log?accion=&usuario=&desde=&hasta=&modulo=&page=&page_size=`
- `GET /api/auditoria/metricas`

### C-06 — Estructura académica
- `GET/POST /api/carreras`, `GET/PUT/DELETE /api/carreras/{id}`
- `GET/POST /api/cohortes`, `GET/PUT/DELETE /api/cohortes/{id}`
- `GET/POST /api/materias`, `GET/PUT/DELETE /api/materias/{id}`

### C-07 — Usuarios
- `GET  /api/usuarios`
- `POST /api/usuarios`
- `PUT  /api/usuarios/{id}`
- `GET  /api/usuarios/{id}`
- `POST /api/usuarios/{id}/roles`
