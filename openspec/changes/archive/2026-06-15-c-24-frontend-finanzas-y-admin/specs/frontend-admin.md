# Spec: Frontend Admin

## Capability
frontend-admin

## Scenarios

### SC-07: Gestión de estructura académica (carreras, cohortes, materias)
- DADO que el usuario tiene rol ADMIN
- CUANDO navega a /admin > tab "Estructura"
- ENTONCES puede listar, crear, editar y eliminar carreras, cohortes y materias

### SC-08: Gestión de usuarios del tenant
- DADO que el usuario tiene rol ADMIN
- CUANDO va al tab "Usuarios"
- ENTONCES ve la lista de usuarios con rol, puede crear uno nuevo, editar y asignar roles

### SC-09: Panel de auditoría con filtros
- DADO que el usuario tiene rol ADMIN
- CUANDO va al tab "Auditoría"
- ENTONCES ve el log paginado con filtros por acción, usuario, fecha y módulo

### SC-10: Métricas de auditoría
- DADO que el usuario está en el panel de auditoría
- CUANDO la sección de métricas carga
- ENTONCES ve KPIs del sistema (total eventos hoy, distribución por acción, usuarios activos)

## Acceptance Criteria
- `useCarreras`, `useCohortes`, `useMaterias` retornan listas
- `useCrearCarrera`, `useActualizarCarrera`, `useEliminarCarrera` (ídem cohortes/materias) son mutations que invalidan la query madre
- `useUsuarios` retorna lista; `useCrearUsuario`, `useActualizarUsuario`, `useAsignarRoles` son mutations
- `useAuditoriaLog(filtros, page)` retorna `{ items, total, page }` con paginación
- `useAuditoriaMetricas` retorna métricas del sistema
- AdminPage renderiza 3 tabs: Estructura / Usuarios / Auditoría
- FiltrosAuditoria emite `onChange` al cambiar cualquier campo; tabla se actualiza
- Todos los hooks tienen al menos 2 test cases
