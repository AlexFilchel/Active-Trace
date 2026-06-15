# Tasks: C-18 — Liquidaciones y Honorarios

> Governance CRÍTICO: módulo financiero. Strict TDD por tarea. No mockear la DB.
> Antes de implementar el servicio de cálculo (tarea 4.2), verificar con el usuario que D2 y D3 del design están confirmados.

## 0. Safety Net

- [x] 0.1 Correr suite existente y capturar baseline. Reportar pre-existing failures sin arreglarlos.

## 1. Migración (DDL + columna + seed de permisos)

- [x] 1.1 Crear `backend/alembic/versions/016_liquidaciones_honorarios.py` (revision `016_liquidaciones_honorarios`, down_revision `015_auditoria_permiso`):
  - `ALTER TABLE materia ADD COLUMN IF NOT EXISTS categoria_plus VARCHAR(50)` (nullable, sin default).
  - DDL de tabla `salario_base`: `(id UUID PK, tenant_id UUID FK, rol VARCHAR(20) NOT NULL, monto DECIMAL(12,2) NOT NULL, desde DATE NOT NULL, hasta DATE NULLABLE, created_at, updated_at, deleted_at)`. Index en `(tenant_id, rol)`.
  - DDL de tabla `salario_plus`: `(id UUID PK, tenant_id UUID FK, grupo VARCHAR(50) NOT NULL, rol VARCHAR(20) NOT NULL, descripcion TEXT, monto DECIMAL(12,2) NOT NULL, desde DATE NOT NULL, hasta DATE NULLABLE, created_at, updated_at, deleted_at)`. Index en `(tenant_id, grupo, rol)`.
  - DDL de tabla `liquidacion`: `(id UUID PK, tenant_id UUID FK, cohorte_id UUID FK → cohorte, periodo VARCHAR(7) NOT NULL, usuario_id UUID FK → usuario, rol VARCHAR(20) NOT NULL, comisiones JSONB, monto_base DECIMAL(12,2), monto_plus DECIMAL(12,2), total DECIMAL(12,2), es_nexo BOOL DEFAULT false, excluido_por_factura BOOL DEFAULT false, estado VARCHAR(10) NOT NULL DEFAULT 'Abierta', created_at, updated_at, deleted_at)`. UK: `(tenant_id, cohorte_id, periodo, usuario_id, rol)`. Index en `(tenant_id, cohorte_id, periodo)`.
  - DDL de tabla `factura`: `(id UUID PK, tenant_id UUID FK, usuario_id UUID FK → usuario, periodo VARCHAR(7) NOT NULL, detalle TEXT, referencia_archivo TEXT, tamano_kb DECIMAL(10,2) NULLABLE, estado VARCHAR(10) NOT NULL DEFAULT 'Pendiente', cargada_at TIMESTAMPTZ NOT NULL DEFAULT now(), abonada_at TIMESTAMPTZ NULLABLE, created_at, updated_at, deleted_at)`. Index en `(tenant_id, usuario_id)`.
  - Seed de permisos: `liquidaciones:ver` → FINANZAS + ADMIN; `liquidaciones:configurar-salarios` → FINANZAS; `liquidaciones:cerrar` → FINANZAS; `liquidaciones:gestionar-facturas` → FINANZAS. Usar `ON CONFLICT ON CONSTRAINT uq_permiso_tenant_nombre DO NOTHING`.
  - `downgrade()`: no-op (permisos pueden quedar).

## 2. Modelos SQLAlchemy

- [x] 2.1 Crear `backend/app/models/liquidaciones.py`
- [x] 2.2 Modificar `backend/app/models/estructura.py`: agregar `categoria_plus`.

## 3. Schemas Pydantic (`extra='forbid'`)

- [x] 3.1 Crear `backend/app/schemas/liquidaciones.py`:
  - `CrearSalarioBaseRequest`, `SalarioBaseResponse`, `EditarSalarioBaseRequest`.
  - `CrearSalarioPlusRequest`, `SalarioPlusResponse`, `EditarSalarioPlusRequest`.
  - `CalcularLiquidacionRequest`: `cohorte_id` (UUID), `periodo` (str pattern `AAAA-MM`).
  - `LiquidacionResponse`: todos los campos de Liquidacion.
  - `LiquidacionKpisResponse`: `cohorte_id`, `periodo`, `estado`, `total_sin_factura`, `total_con_factura`, `total_nexo`, `cantidad_docentes`, `cantidad_facturantes`.
  - `CrearFacturaRequest`, `FacturaResponse`.
- [x] 3.2 Modificar `backend/app/schemas/estructura.py` (si existe) o el schema de Materia: agregar campo opcional `categoria_plus: str | None = None`.

## 4. Repositories

- [x] 4.1 Crear `backend/app/repositories/liquidaciones.py`:
  - `SalarioBaseRepository(TenantScopedRepository)`: `crear`, `listar(rol?, periodo?)`, `editar`, `soft_delete`. Método `vigente_para(rol, periodo)` → retorna el registro vigente o None.
  - `SalarioPlusRepository(TenantScopedRepository)`: `crear`, `listar(grupo?, rol?, periodo?)`, `editar`, `soft_delete`. Método `vigentes_para_periodo(periodo)` → list de todos los plus activos ese mes.
  - `LiquidacionRepository(TenantScopedRepository)`: `upsert_para_periodo(cohorte_id, periodo, rows)`, `listar(cohorte_id?, periodo?, estado?, usuario_id?)`, `cerrar_periodo(cohorte_id, periodo)` → UPDATE estado Abierta→Cerrada, `estado_periodo(cohorte_id, periodo)` → 'Abierta'|'Cerrada'|None.
  - `FacturaRepository(TenantScopedRepository)`: `crear`, `listar(usuario_id?, estado?, periodo?)`, `abonar(id)`.

## 5. Service de cálculo (CHECKPOINT — revisar D2 y D3 antes de implementar)

- [x] 5.1 Crear `backend/app/services/liquidacion_service.py` con `LiquidacionService(session, tenant_id)`:
  - `calcular(cohorte_id, periodo)`:
    1. Verifica que `estado_periodo != 'Cerrada'` → si cerrada, lanza 409.
    2. Carga todas las asignaciones vigentes en el período para la cohorte (via `AsignacionRepository` o query directa).
    3. Agrupa por `(usuario_id, rol)`.
    4. Para cada grupo: busca `SalarioBase.vigente_para(rol, periodo)` → `monto_base`.
    5. Para cada comisión del docente: busca `materia.categoria_plus`; si no es null, busca `SalarioPlus` vigente para `(grupo=categoria_plus, rol, periodo)` → suma `N × monto_plus`.
    6. Determina `excluido_por_factura` desde `usuario.facturador`.
    7. Determina `es_nexo` si rol == 'NEXO'.
    8. Hace `upsert_para_periodo` con las filas calculadas.
    9. Audita `LIQUIDACION_CALCULAR`.
  - `cerrar(cohorte_id, periodo)`: llama `repo.cerrar_periodo`, audita `LIQUIDACION_CERRAR`.
  - `kpis(cohorte_id, periodo)` → `LiquidacionKpisResponse`.
- [x] 5.2 Crear `backend/app/services/factura_service.py` con `FacturaService(session, tenant_id)`:
  - `crear(payload)`: verifica `usuario.facturador == True` → 422 si no. Persiste. Audita `FACTURA_CREAR`.
  - `abonar(id)`: cambia estado → Abonada, setea `abonada_at`. Audita `FACTURA_ABONAR`.
  - `listar(usuario_id?, estado?, periodo?)`.

## 6. Routers

- [x] 6.1 Crear `backend/app/api/v1/routers/salarios.py`.
- [x] 6.2 Crear `backend/app/api/v1/routers/liquidaciones.py`.
- [x] 6.3 Crear `backend/app/api/v1/routers/facturas.py`.
- [x] 6.4 Registrar los 3 routers en `backend/app/main.py`.

## 7. Tests (Strict TDD — Safety Net → Red → Green → Triangulate → Refactor)

- [x] 7.1 `test_salarios_crud_tdd.py`: CRUD de SalarioBase y SalarioPlus; vigencia temporal (`vigente_para`); 403 sin permiso; isolamiento tenant.
- [x] 7.2 `test_liquidacion_calculo_tdd.py`: cálculo correcto con 1 comisión; acumulación N comisiones misma categoría; materia sin categoría no suma plus; docente facturante marcado como excluido; recálculo idempotente sobre período abierto; 409 sobre período cerrado.
- [x] 7.3 `test_liquidacion_cierre_tdd.py`: cierre cambia estado a Cerrada; 409 al recalcular después de cerrar; 403 sin `liquidaciones:cerrar`; KPIs contables (`total_sin_factura`, NEXO separado).
- [x] 7.4 `test_facturas_crud_tdd.py`: crear factura para docente facturante; 422 para docente no facturante; abonar cambia estado + setea `abonada_at`; listar con filtros; isolamiento tenant.
