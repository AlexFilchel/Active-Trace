## Why

El sistema carece del módulo financiero central: no existe forma de calcular, visualizar ni cerrar la liquidación mensual de honorarios docentes ni de gestionar los comprobantes de los docentes que facturan. Sin este módulo, el equipo de FINANZAS no puede operar el ciclo de pago desde la plataforma.

Las preguntas abiertas que bloqueaban este change (PA-22 y PA-23) fueron cerradas: la categoría de Plus se modela como un campo `categoria_plus` nullable en `Materia`, y la acumulación de Plus sigue la fórmula `N × Plus(categoría, rol)` sin tope, confirmada por RN-33 y RN-34.

## What Changes

- **Nuevo**: tabla `salario_base` — grilla de montos base por rol con vigencia temporal (RN-31, RN-32).
- **Nuevo**: tabla `salario_plus` — complementos por (grupo de materias × rol) con vigencia (RN-33).
- **Nuevo**: tabla `liquidacion` — registro de honorarios por docente × cohorte × período; inmutable al cerrar (RN-34, RN-37).
- **Nuevo**: tabla `factura` — comprobantes de docentes en modalidad de facturación independiente (RN-35, RN-39, RN-40).
- **Modificado**: tabla `materia` — columna `categoria_plus VARCHAR(50) NULLABLE` para mapear materias a grupos de Plus (PA-22 cerrada).
- **Nuevos endpoints** bajo `/api/liquidaciones` y `/api/facturas`:
  - Grilla salarial: CRUD de bases y plus con filtros de vigencia.
  - Cálculo y vista de liquidación por (cohorte, período) con desglose por rol.
  - Cierre de liquidación (transición Abierta → Cerrada, inmutable).
  - Historial de liquidaciones cerradas.
  - Gestión de facturas: carga, listado, cambio de estado Pendiente ↔ Abonada.
- **Nuevos permisos**: `liquidaciones:ver`, `liquidaciones:configurar-salarios`, `liquidaciones:cerrar`, `liquidaciones:gestionar-facturas`.
- **Nuevas acciones de auditoría**: `LIQUIDACION_CERRAR`, `SALARIO_CREAR`, `SALARIO_EDITAR`, `FACTURA_CREAR`, `FACTURA_ABONAR`.

## Capabilities

### New Capabilities

- `liquidaciones-y-honorarios`: grilla salarial, cálculo de liquidaciones por período, cierre inmutable, facturas de docentes independientes, KPIs contables (sin factura / con factura / NEXO separado).

### Modified Capabilities

- `estructura-academica`: `Materia` agrega `categoria_plus` (campo nuevo, sin breaking change para clientes existentes — nullable, default NULL).

## Impact

- **Migración Alembic**: revisión `016_liquidaciones_honorarios` — DDL de 4 tablas nuevas + columna en `materia` + seed de permisos para FINANZAS y ADMIN.
- **Archivos de código nuevos**: `models/liquidaciones.py`, `schemas/liquidaciones.py`, `repositories/liquidaciones.py`, `services/liquidacion_service.py`, `routers/liquidaciones.py`, `routers/facturas.py`.
- **Archivos modificados**: `models/estructura.py` (columna `categoria_plus` en `Materia`), `main.py` (registro de routers).
- **Governance CRÍTICO**: módulo financiero — implementar con checkpoints; no escribir código de cálculo sin revisión del diseño.
- **Dependencias satisfechas**: C-07 (usuarios), C-06 (estructura académica con Materia), C-04 (RBAC).
