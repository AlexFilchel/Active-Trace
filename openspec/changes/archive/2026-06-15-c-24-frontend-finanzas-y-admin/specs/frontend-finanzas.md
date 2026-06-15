# Spec: Frontend Finanzas

## Capability
frontend-finanzas

## Scenarios

### SC-01: Ver liquidaciones del período con KPIs
- DADO que el usuario tiene rol FINANZAS o ADMIN
- CUANDO navega a /liquidaciones y selecciona un período
- ENTONCES ve KPIs (total docentes, total honorarios, estado) y la tabla de detalle segmentada

### SC-02: Segmentación de liquidación (General / NEXO / Factura)
- DADO que hay una liquidación calculada para el período
- CUANDO el usuario cambia de tab
- ENTONCES la tabla muestra solo los ítems del segmento seleccionado

### SC-03: Cerrar liquidación
- DADO que la liquidación está en estado ABIERTA
- CUANDO el usuario presiona "Cerrar liquidación"
- ENTONCES se llama PUT /api/liquidaciones/{id}/cerrar y el estado cambia a CERRADA

### SC-04: Ver historial de liquidaciones anteriores
- DADO que existen liquidaciones archivadas
- CUANDO el usuario va al tab "Historial"
- ENTONCES ve la lista de períodos anteriores con estado y totales

### SC-05: ABM grilla salarial
- DADO que el usuario tiene rol FINANZAS o ADMIN
- CUANDO abre la sección "Grilla Salarial"
- ENTONCES puede listar, crear, editar y eliminar entradas (categoría + salario base)

### SC-06: Gestión de facturas
- DADO que hay facturas registradas
- CUANDO el usuario abre "Facturas"
- ENTONCES puede listar facturas, registrar una nueva y cambiar estado (aprobar/rechazar)

## Acceptance Criteria
- `useLiquidaciones(periodo)` retorna datos del GET /api/liquidaciones
- `useCerrarLiquidacion` llama PUT y invalida la query de liquidaciones
- `useGrillasSalariales` retorna array; `useCrearGrilla`, `useActualizarGrilla`, `useEliminarGrilla` son mutations
- `useFacturas` retorna lista; `useCrearFactura`, `useActualizarEstadoFactura` son mutations
- LiquidacionesPage renderiza KPIs, tabs General/NEXO/Facturas, botón cerrar
- Todos los hooks tienen al menos 2 test cases (happy path + edge)
