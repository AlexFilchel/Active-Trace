# Design: C-23 — Frontend Coordinación

## Architecture

Each domain follows the **feature-based module** pattern established by `features/comisiones/`:

```
features/{name}/
  types/index.ts          — domain types
  services/{name}Service.ts — apiClient wrappers
  hooks/use{Entity}.ts    — TanStack Query hooks (useQuery / useMutation)
  components/*.tsx        — pure presentational components < 200 LOC
  pages/{Name}Page.tsx    — single orchestrator page < 200 LOC
```

## Feature Modules

### 1. equipos (`features/equipos/`)
Types: `Equipo`, `MiembroEquipo`, `EquipoCreate`, `ClonarEquipoPayload`

Service methods:
- `getEquipos()` → GET /api/equipos
- `createEquipo(data)` → POST /api/equipos
- `updateEquipo(id, data)` → PUT /api/equipos/{id}
- `deleteEquipo(id)` → DELETE /api/equipos/{id}
- `clonarEquipo(id, data)` → POST /api/equipos/{id}/clonar
- `altaMasiva(data)` → POST /api/equipos/masivo
- `getMiembros(id)` → GET /api/equipos/{id}/miembros
- `addMiembro(id, payload)` → POST /api/equipos/{id}/miembros
- `removeMiembro(id, userId)` → DELETE /api/equipos/{id}/miembros/{userId}

Hooks: `useEquipos`, `useCreateEquipo`, `useDeleteEquipo`, `useClonarEquipo`

Page: `EquiposPage` — tabs: Lista | Miembros | Alta masiva

### 2. avisos (`features/avisos/`)
Types: `Aviso`, `AvisoScope`, `AvisoCreate`, `Acknowledgment`

Service methods:
- `getAvisos()` → GET /api/avisos
- `createAviso(data)` → POST /api/avisos
- `updateAviso(id, data)` → PUT /api/avisos/{id}
- `deleteAviso(id)` → DELETE /api/avisos/{id}
- `getAcknowledgments(id)` → GET /api/avisos/{id}/acknowledgments

Hooks: `useAvisos`, `useCreateAviso`, `useDeleteAviso`

Page: `AvisosPage` — list + create form panel

### 3. tareas (`features/tareas/`)
Types: `Tarea`, `TareaEstado`, `TareaCreate`, `Comentario`

TareaEstado: `'pendiente' | 'en_progreso' | 'completada'`

Service methods:
- `getTareas()` → GET /api/tareas
- `createTarea(data)` → POST /api/tareas
- `updateTarea(id, data)` → PUT /api/tareas/{id} (includes estado changes)
- `deleteTarea(id)` → DELETE /api/tareas/{id}
- `getComentarios(id)` → GET /api/tareas/{id}/comentarios
- `addComentario(id, body)` → POST /api/tareas/{id}/comentarios

Hooks: `useTareas`, `useCreateTarea`, `useUpdateTarea`, `useDeleteTarea`

Page: `TareasPage` — Kanban-style columns per estado + detail panel

### 4. monitores (`features/monitores/`)
Types: `MonitorItem`, `EntregaMonitor`, `MonitorFilter`

Service methods:
- `getMonitorGeneral(filters?)` → GET /api/alumnos/monitor (F2.7 — reuses alumnos endpoint)
- `getMonitorEntregas(filters?)` → GET /api/calificaciones/entregas-sin-corregir (F2.9)

Hooks: `useMonitorGeneral`, `useMonitorEntregas`

Page: `MonitoresPage` — tabs: General | Entregas

### 5. encuentros (`features/encuentros/`)
Types: `Encuentro`, `Guardia`, `EncuentroCreate`

Service methods:
- `getEncuentros()` → GET /api/encuentros
- `createEncuentro(data)` → POST /api/encuentros
- `updateEncuentro(id, data)` → PUT /api/encuentros/{id}
- `deleteEncuentro(id)` → DELETE /api/encuentros/{id}
- `getGuardias()` → GET /api/guardias
- `createGuardia(data)` → POST /api/guardias

Hooks: `useEncuentros`, `useCreateEncuentro`, `useGuardias`

Page: `EncuentrosPage` — tabs: Encuentros | Guardias

### 6. coloquios (`features/coloquios/`)
Types: `Coloquio`, `ColoquioDia`, `Candidato`, `ColoquioCreate`

Service methods:
- `getColoquios()` → GET /api/coloquios
- `createColoquio(data)` → POST /api/coloquios
- `getDias(id)` → GET /api/coloquios/{id}/dias
- `addDia(id, data)` → POST /api/coloquios/{id}/dias
- `getCandidatos(id)` → GET /api/coloquios/{id}/candidatos
- `addCandidato(id, alumnoId)` → POST /api/coloquios/{id}/candidatos
- `reservar(id, diaId, alumnoId)` → POST /api/coloquios/{id}/dias/{diaId}/reservar
- `setResultado(id, alumnoId, resultado)` → PUT /api/coloquios/{id}/candidatos/{alumnoId}/resultado

Hooks: `useColoquios`, `useCreateColoquio`, `useColoquioDias`, `useColoquioCandidatos`

Page: `ColoquiosPage` — list + detail view with tabs: Días | Candidatos | Resultados

## Router additions

Add to `frontend/src/router/index.tsx`:
```
/equipos      → EquiposPage
/avisos       → AvisosPage
/tareas       → TareasPage
/monitores    → MonitoresPage
/encuentros   → EncuentrosPage
/coloquios    → ColoquiosPage
```

## Nav additions

Add to `AuthenticatedLayout.tsx` NAV_ENTRIES:
```ts
{ label: 'Equipos',    path: '/equipos',    roles: ['COORDINADOR', 'ADMIN'] },
{ label: 'Avisos',     path: '/avisos',     roles: ['COORDINADOR', 'ADMIN'] },
{ label: 'Tareas',     path: '/tareas',     roles: ['COORDINADOR', 'ADMIN'] },
{ label: 'Monitores',  path: '/monitores',  roles: ['COORDINADOR', 'ADMIN'] },
{ label: 'Encuentros', path: '/encuentros', roles: ['COORDINADOR', 'ADMIN'] },
{ label: 'Coloquios',  path: '/coloquios',  roles: ['COORDINADOR', 'ADMIN'] },
```

## Test Strategy

- **Service tests** (Vitest + MSW): test each service method against MSW handlers  
- **Hook tests** (Vitest + RTL + MSW): test query hooks via renderHook  
- **Page smoke tests**: render page, check MSW-stubbed list appears  
- TDD cycle strictly: RED → GREEN → TRIANGULATE → REFACTOR
- MSW handlers added to `frontend/src/test/server.ts`

## File Count Estimate

~60 new files. All components < 200 LOC, pages < 200 LOC.
