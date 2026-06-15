## ADDED Requirements

### Requirement: Grilla salarial configurable por tenant

El sistema SHALL permitir al rol FINANZAS gestionar una grilla de salarios base por rol y una grilla de plus por (categoría de materia × rol), ambas con vigencia temporal.

#### Scenario: Crear salario base vigente
- **WHEN** FINANZAS crea un `SalarioBase` con rol=PROFESOR, monto=5000, desde=2026-01-01, hasta=null
- **THEN** el sistema persiste el registro y audita `SALARIO_CREAR`

#### Scenario: Crear plus por categoría
- **WHEN** FINANZAS crea un `SalarioPlus` con grupo="PROG", rol=PROFESOR, monto=800, desde=2026-01-01
- **THEN** el sistema persiste el registro y audita `SALARIO_CREAR`

#### Scenario: Solo FINANZAS puede configurar salarios
- **WHEN** un usuario sin `liquidaciones:configurar-salarios` intenta crear o editar un salario
- **THEN** el sistema responde 403

---

### Requirement: Cálculo de liquidación mensual

El sistema SHALL calcular automáticamente la liquidación de cada docente para una dupla (cohorte, período) usando la fórmula `Total = Base(rol, período) + Σ(Plus(categoria_plus_materia, rol) × N_comisiones)`.

#### Scenario: Docente con comisiones de una sola categoría
- **WHEN** FINANZAS solicita la liquidación de un PROFESOR con 2 comisiones de materias con `categoria_plus="PROG"` para el período 2026-06
- **THEN** el sistema retorna `monto_plus = 2 × SalarioPlus(grupo="PROG", rol=PROFESOR, vigente en 2026-06)`

#### Scenario: Docente con comisiones de múltiples categorías
- **WHEN** el docente tiene 1 comisión "PROG" y 1 comisión "BD"
- **THEN** el sistema acumula `Plus("PROG", rol) + Plus("BD", rol)` — una vez cada uno

#### Scenario: Materia sin categoría no genera plus
- **WHEN** una materia tiene `categoria_plus = NULL`
- **THEN** esa comisión no aporta monto al plus del docente

#### Scenario: Docente facturante se excluye del total
- **WHEN** el docente tiene `facturador = true` en su perfil
- **THEN** la liquidación se genera con `excluido_por_factura = true` y no se incluye en el total general

---

### Requirement: Cierre de liquidación

El sistema SHALL convertir la liquidación de un período en inmutable al ejecutar el cierre.

#### Scenario: Cerrar liquidación abierta
- **WHEN** FINANZAS cierra la liquidación de (cohorte, 2026-06)
- **THEN** todos los registros de `Liquidacion` del período pasan a estado `Cerrada` y se audita `LIQUIDACION_CERRAR`

#### Scenario: Liquidación cerrada no modificable
- **WHEN** se intenta recalcular o editar una liquidación con estado `Cerrada`
- **THEN** el sistema responde 409 Conflict

#### Scenario: Solo FINANZAS puede cerrar
- **WHEN** un usuario sin `liquidaciones:cerrar` intenta cerrar una liquidación
- **THEN** el sistema responde 403

---

### Requirement: Vista de liquidaciones con separación contable

El sistema SHALL exponer la vista de liquidación con tres segmentos: dependientes generales, NEXO y facturantes.

#### Scenario: KPIs de cabecera
- **WHEN** FINANZAS consulta la liquidación de (cohorte, período)
- **THEN** la respuesta incluye `total_sin_factura` (sum de dependientes + NEXO) y `total_con_factura` (informativo, suma de todos incluyendo facturantes)

#### Scenario: NEXO separado pero incluido en total
- **WHEN** hay docentes con `es_nexo = true`
- **THEN** sus montos aparecen en segmento diferenciado pero se suman a `total_sin_factura`

---

### Requirement: Gestión de facturas de docentes independientes

El sistema SHALL permitir a FINANZAS gestionar comprobantes de docentes facturantes.

#### Scenario: Crear factura
- **WHEN** FINANZAS registra una factura para un docente facturante con período, detalle y referencia de archivo
- **THEN** la factura se crea en estado `Pendiente` y se audita `FACTURA_CREAR`

#### Scenario: Marcar factura como abonada
- **WHEN** FINANZAS cambia el estado de una factura a `Abonada`
- **THEN** se registra `abonada_at = now()` y se audita `FACTURA_ABONAR`

#### Scenario: Solo se pueden registrar facturas para docentes facturantes
- **WHEN** se intenta crear una factura para un docente con `facturador = false`
- **THEN** el sistema responde 422
