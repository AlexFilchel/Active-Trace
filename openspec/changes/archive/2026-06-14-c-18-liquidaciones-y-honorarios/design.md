## Context

C-18 introduce el módulo financiero: grilla salarial, cálculo de liquidaciones mensuales y gestión de facturas. Depende de C-06 (Materia) y C-07 (Usuario con campo `facturador`). Las preguntas PA-22 y PA-23 están cerradas: `categoria_plus` vive en `Materia`, y la acumulación es siempre N × Plus sin tope.

Governance: **CRÍTICO** — módulo financiero. Checkpoints requeridos antes de implementar el servicio de cálculo.

## Goals / Non-Goals

**Goals:**
- Modelos persistentes para SalarioBase, SalarioPlus, Liquidacion y Factura.
- Columna `categoria_plus` en `Materia` (migración additive, nullable).
- Endpoints CRUD para grilla salarial y facturas.
- Endpoint de cálculo de liquidación (genera filas por docente activo en la cohorte).
- Endpoint de cierre (Abierta → Cerrada, inmutable).
- Vista con KPIs contables: `total_sin_factura`, `total_con_factura`.
- Seed de permisos: `liquidaciones:ver`, `liquidaciones:configurar-salarios`, `liquidaciones:cerrar`, `liquidaciones:gestionar-facturas`.

**Non-Goals:**
- Exportación a PDF/Excel (post-MVP).
- Integración con sistemas de pago o bancos.
- Automatización del envío de recibos.
- Módulo de nómina completo (solo liquidación de honorarios docentes).

## Decisions

### D1 — `categoria_plus` como campo en Materia (PA-22 cerrada)

`Materia.categoria_plus: VARCHAR(50) NULLABLE`. Texto libre por tenant. Cualquier valor que coincida con `SalarioPlus.grupo` (comparación exacta, case-sensitive) activa el Plus. El ADMIN/COORDINADOR lo define al crear/editar la materia via el endpoint existente de estructura. No se crea tabla de catálogo separada — la grilla de Plus actúa como catálogo implícito.

### D2 — Acumulación N × Plus sin tope (PA-23 cerrada)

Fórmula exacta de RN-34: `Σ(Plus(grupo, rol) × N_comisiones_de_ese_grupo)`. N_comisiones se cuenta desde `asignacion` donde `materia.categoria_plus = plus.grupo` y la asignación estaba vigente en el período calculado. Sin tope explícito.

### D3 — Liquidación como registro generado, no calculado on-the-fly

El endpoint `POST /api/liquidaciones/calcular` genera y persiste filas `Liquidacion` para todos los docentes activos en (cohorte, período). Es idempotente: si ya existen filas para ese período en estado Abierta, las recalcula. Si el período está Cerrado, devuelve 409.

### D4 — Cierre inmutable via estado, no trigger de DB

El cierre (`POST /api/liquidaciones/{cohorte_id}/{periodo}/cerrar`) hace UPDATE de estado `Abierta → Cerrada` en bloque. La inmutabilidad se refuerza a nivel de servicio: `LiquidacionService` comprueba estado antes de cualquier write. No se replica el trigger de AuditLog (que es append-only por otra razón).

### D5 — Factura solo para docentes con `facturador = true`

Validación en `FacturaService.crear()`: carga el `Usuario` por `usuario_id` y verifica `facturador == True`. Si no, lanza `422`. El campo `facturador` ya existe en `Usuario` (C-07).

### D6 — Permisos por funcionalidad, fail-closed

| Permiso | Roles que lo reciben en seed | Operaciones cubiertas |
|---|---|---|
| `liquidaciones:ver` | FINANZAS, ADMIN | GET liquidaciones, historial, KPIs |
| `liquidaciones:configurar-salarios` | FINANZAS | CRUD SalarioBase y SalarioPlus |
| `liquidaciones:cerrar` | FINANZAS | POST /cerrar |
| `liquidaciones:gestionar-facturas` | FINANZAS | CRUD Facturas + cambio de estado |

### D7 — Estructura de tablas

**`salario_base`**: `(id, tenant_id, rol ENUM, monto DECIMAL(12,2), desde DATE, hasta DATE NULLABLE)`. UK: `(tenant_id, rol, desde)`.

**`salario_plus`**: `(id, tenant_id, grupo VARCHAR(50), rol ENUM, descripcion TEXT, monto DECIMAL(12,2), desde DATE, hasta DATE NULLABLE)`. UK: `(tenant_id, grupo, rol, desde)`.

**`liquidacion`**: `(id, tenant_id, cohorte_id FK, periodo VARCHAR(7), usuario_id FK, rol ENUM, comisiones JSONB, monto_base DECIMAL(12,2), monto_plus DECIMAL(12,2), total DECIMAL(12,2), es_nexo BOOL, excluido_por_factura BOOL, estado ENUM('Abierta','Cerrada'))`. UK: `(tenant_id, cohorte_id, periodo, usuario_id, rol)`. Index: `(tenant_id, cohorte_id, periodo)`.

**`factura`**: `(id, tenant_id, usuario_id FK, periodo VARCHAR(7), detalle TEXT, referencia_archivo TEXT, tamano_kb DECIMAL(10,2) NULLABLE, estado ENUM('Pendiente','Abonada'), cargada_at TIMESTAMPTZ, abonada_at TIMESTAMPTZ NULLABLE)`. Index: `(tenant_id, usuario_id)`.

Todas las tablas usan `TenantScopedMixin` (tenant_id + soft-delete + updated_at). Liquidacion y Factura tienen `created_at` por el mixin base.

### D8 — Endpoints

```
# Grilla salarial
POST   /api/salarios/base                     — crear SalarioBase
GET    /api/salarios/base                     — listar (filtro: rol, periodo)
PATCH  /api/salarios/base/{id}               — editar monto/hasta
DELETE /api/salarios/base/{id}               — soft-delete

POST   /api/salarios/plus                     — crear SalarioPlus
GET    /api/salarios/plus                     — listar (filtro: grupo, rol, periodo)
PATCH  /api/salarios/plus/{id}               — editar
DELETE /api/salarios/plus/{id}               — soft-delete

# Liquidaciones
POST   /api/liquidaciones/calcular            — genera/recalcula para (cohorte_id, periodo)
GET    /api/liquidaciones                     — lista (filtro: cohorte_id, periodo, estado)
GET    /api/liquidaciones/{cohorte_id}/{periodo}/kpis  — totales contables
POST   /api/liquidaciones/{cohorte_id}/{periodo}/cerrar — cierre inmutable
GET    /api/liquidaciones/historial           — liquidaciones cerradas

# Facturas
POST   /api/facturas                          — crear factura
GET    /api/facturas                          — listar (filtro: usuario_id, estado, periodo)
PATCH  /api/facturas/{id}/abonar             — marcar como Abonada
```

## Risks / Trade-offs

- **Recálculo sobre período abierto**: si los datos de asignaciones cambian entre el primer cálculo y el cierre, el resultado puede variar. Mitigado: `POST /calcular` es idempotente; el usuario puede recalcular antes de cerrar.
- **`categoria_plus` texto libre**: si el tenant escribe el grupo con diferente capitalización que en la grilla, no se genera Plus (silently). Documentado en spec; se puede agregar normalización (lower-case) en un change futuro.
- **Sin migración de datos**: la columna `categoria_plus` se agrega como nullable — los registros existentes quedan con NULL y no generan Plus hasta que un ADMIN los categorice. Es el comportamiento correcto para MVP.
