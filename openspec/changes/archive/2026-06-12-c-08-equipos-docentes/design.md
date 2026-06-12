## Context

C-07 entregó el modelo `Asignacion` con CRUD base y vigencia temporal. Este change construye encima de ese modelo las operaciones de negocio de alto nivel que el COORDINADOR necesita para gestionar equipos docentes: vista de mis-equipos, asignación masiva, clonado entre cohortes, modificación de vigencia en bloque y exportación. No se crean tablas nuevas; toda la lógica opera sobre `asignacion`.

El dominio de governance es **ALTO**: las operaciones de clonado y asignación masiva crean o modifican múltiples asignaciones en una transacción, lo que impacta directamente en qué docentes tienen acceso a qué materias.

## Goals / Non-Goals

**Goals:**
- Exponer `/api/equipos/*` con las operaciones F4.2–F4.7 bajo el permiso `equipos:asignar`.
- Implementar clonado transaccional de equipo (RN-12): duplicar N asignaciones hacia un destino en una sola operación atómica.
- Asignación masiva con autocompletado server-side para búsqueda de docentes (RN-30).
- Modificación de vigencia en bloque: un solo request actualiza `desde`/`hasta` de todas las asignaciones de un equipo.
- Exportación a CSV/XLSX de las asignaciones del equipo.
- Registro de auditoría `ASIGNACION_MODIFICAR` en operaciones que modifican asignaciones.

**Non-Goals:**
- Gestión de usuarios (alta/baja de docentes) — eso es C-07 (`/api/admin/usuarios`).
- Lógica de liquidación o cálculo de honorarios asociados a asignaciones — eso es C-18.
- Frontend — eso es C-23.

## Decisions

### 1. Clonado es una operación de Service, no de Repository

El clonado copia N asignaciones en una transacción atómica. La lógica vive en `equipo_service.py`:
1. Carga todas las asignaciones vigentes del origen (materia × carrera × cohorte).
2. Por cada una crea una nueva `Asignacion` con el destino y las nuevas fechas de vigencia.
3. Hace commit de todo en una sola transacción SQLAlchemy.

**Alternativa descartada**: bulk-insert directo en el router — viola la regla de no lógica en routers.

### 2. Autocompletado de docentes es un endpoint dedicado

`GET /api/equipos/docentes/buscar?q=<término>` devuelve hasta 20 matches por nombre/apellido. Separado del endpoint de asignación masiva para reutilización y para no acoplar la búsqueda al payload de asignación.

**Alternativa descartada**: filtro inline en el endpoint de asignaciones — mezcla búsqueda con listado y dificulta el testing.

### 3. Modificación de vigencia en bloque usa bulk UPDATE con scope de tenant

`PATCH /api/equipos/{equipo_id}/vigencia` recibe `{desde, hasta}` y ejecuta un UPDATE filtrado por `tenant_id + materia_id + carrera_id + cohorte_id`. El scope de tenant es obligatorio — sin él el query no debe ejecutarse.

### 4. Exportación síncrona (no background job)

Los equipos docentes raramente superan los 50 registros. La exportación se genera síncronamente en el request, sin encolar en el worker. Si en el futuro el volumen crece, se mueve al worker sin cambiar el contrato de la API (el endpoint puede devolver un job_id en ese momento).

### 5. "Equipo" no es una entidad nueva

No se crea una tabla `Equipo`. Un equipo es el conjunto de `Asignacion` que comparten `(tenant_id, materia_id, carrera_id, cohorte_id)`. Esta clave compuesta es el identificador lógico del equipo en todos los endpoints.

## Risks / Trade-offs

- **[Riesgo] Clonado masivo en una transacción larga** → Mitigation: el número de docentes por materia es acotado (típicamente < 20). Si en el futuro se detecta latencia, se puede chunkar el INSERT en lotes de 50 dentro de la misma transacción.
- **[Riesgo] Bulk UPDATE de vigencias sin confirmación** → Mitigation: el endpoint requiere que el frontend muestre una preview antes de confirmar; el backend registra `ASIGNACION_MODIFICAR` con `filas_afectadas` en el audit log.
- **[Trade-off] Exportación síncrona** → Simple de implementar y suficiente para el volumen actual. Acepta latencia si el equipo es grande (poco probable), a cambio de no necesitar polling de estado de job.
