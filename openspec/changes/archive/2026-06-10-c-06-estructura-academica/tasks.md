## 1. Modelos SQLAlchemy

- [x] 1.1 Escribir test RED para `Carrera`: unicidad `(tenant_id, codigo)`, soft delete, estado por defecto "Activa" — el modelo no existe aún
- [x] 1.2 Implementar modelo `Carrera` en `backend/app/models/estructura.py` con `TenantScopedMixin`, campos `codigo`, `nombre`, `estado` y constraint de unicidad — pasar a GREEN
- [x] 1.3 Triangular: agregar test de mismo código en tenants distintos (deben coexistir) y test de soft delete
- [x] 1.4 Escribir test RED para `Cohorte`: unicidad `(tenant_id, carrera_id, nombre)`, FK a `Carrera`, campos `anio`, `vig_desde`, `vig_hasta`, `estado`
- [x] 1.5 Implementar modelo `Cohorte` en `backend/app/models/estructura.py` — pasar a GREEN
- [x] 1.6 Triangular: cohortes de igual nombre en distintas carreras del mismo tenant coexisten; cohorte con `carrera_id` de otro tenant falla
- [x] 1.7 Escribir test RED para `Materia`: unicidad `(tenant_id, codigo)`, campos `codigo`, `nombre`, `estado`
- [x] 1.8 Implementar modelo `Materia` en `backend/app/models/estructura.py` — pasar a GREEN
- [x] 1.9 Triangular: mismo código en tenants distintos coexiste; soft delete funciona
- [x] 1.10 Registrar los tres modelos en `backend/app/models/__init__.py`

## 2. Migración Alembic 004

- [x] 2.1 Crear `backend/alembic/versions/004_estructura_academica.py` con `upgrade`: crea tablas `carrera`, `cohorte`, `materia` con todos los campos, constraints de unicidad e índices sobre `tenant_id` y FKs
- [x] 2.2 Implementar `downgrade` que elimina las tres tablas en orden inverso (materia → cohorte → carrera)
- [x] 2.3 Añadir al `upgrade` el seed idempotente del permiso `estructura:gestionar` en el rol ADMIN de todos los tenants existentes (`INSERT ... ON CONFLICT DO NOTHING`)
- [x] 2.4 Test: ejecutar `alembic upgrade 004` + verificar que las tablas existen y el permiso fue sembrado; ejecutar dos veces para confirmar idempotencia

## 3. Repositories

- [x] 3.1 Escribir test RED para `CarreraRepository`: `list_by_tenant` devuelve solo registros del tenant correcto; `get_by_id` devuelve 404-equivalent si es de otro tenant
- [x] 3.2 Implementar `CarreraRepository` en `backend/app/repositories/estructura.py` heredando `BaseRepository` — pasar a GREEN
- [x] 3.3 Triangular: `get_by_codigo` por tenant; listado excluye soft-deleted
- [x] 3.4 Escribir test RED + implementar `CohortRepository`: filtra por `tenant_id`; soporta filtro opcional por `carrera_id`
- [x] 3.5 Triangular `CohortRepository`: cohorte de otro tenant no visible; filtro por `carrera_id` funciona correctamente
- [x] 3.6 Escribir test RED + implementar `MateriaRepository`: filtra por `tenant_id`; soporta filtro opcional por `estado`
- [x] 3.7 Triangular `MateriaRepository`: materia de otro tenant no visible; filtro por `estado` funciona
- [x] 3.8 Registrar los tres repositories en `backend/app/repositories/__init__.py`

## 4. Schemas Pydantic v2

- [x] 4.1 Crear `backend/app/schemas/estructura.py` con schemas para `Carrera`: `CarreraCreate` (`codigo`, `nombre`), `CarreraUpdate` (`nombre?`, `estado?`), `CarreraResponse` (incluye `id`, `tenant_id`, `created_at`); todos con `extra='forbid'`
- [x] 4.2 Test: `CarreraCreate` con `tenant_id` en el body lanza `ValidationError`; campo desconocido lanza `ValidationError`
- [x] 4.3 Agregar schemas `Cohorte`: `CohorteCreate` (`carrera_id`, `nombre`, `anio`, `vig_desde`, `vig_hasta?`), `CohorteUpdate`, `CohorteResponse`
- [x] 4.4 Agregar schemas `Materia`: `MateriaCreate` (`codigo`, `nombre`), `MateriaUpdate` (`nombre?`, `estado?`), `MateriaResponse`

## 5. Services con reglas de negocio

- [x] 5.1 Escribir test RED para `EstructuraService.crear_carrera`: crea carrera y la retorna; duplicado de código por tenant lanza error 409
- [x] 5.2 Implementar `EstructuraService` en `backend/app/services/estructura.py` con `crear_carrera`, `listar_carreras`, `obtener_carrera`, `actualizar_carrera`, `eliminar_carrera` — pasar a GREEN
- [x] 5.3 Triangular: actualización de estado Activa→Inactiva funciona; obtener carrera de otro tenant lanza 404
- [x] 5.4 Escribir test RED para `EstructuraService.crear_cohorte`: intento de crear cohorte Activa para carrera Inactiva lanza HTTP 422
- [x] 5.5 Implementar `crear_cohorte`, `listar_cohortes`, `obtener_cohorte`, `actualizar_cohorte`, `eliminar_cohorte` con la validación de estado de carrera — pasar a GREEN
- [x] 5.6 Triangular: crear cohorte en carrera Activa funciona; inactivar carrera no afecta cohortes existentes
- [x] 5.7 Escribir test RED + implementar métodos CRUD de `Materia` en el service — pasar a GREEN
- [x] 5.8 Triangular: duplicado de código de materia por tenant lanza 409; materia de otro tenant no visible

## 6. Routers / Endpoints ABM

- [x] 6.1 Crear `backend/app/api/v1/routers/estructura.py` con router de `carreras`: `GET /api/admin/carreras`, `POST /api/admin/carreras`, `GET /api/admin/carreras/{id}`, `PATCH /api/admin/carreras/{id}`, `DELETE /api/admin/carreras/{id}`; todos con `require_permission("estructura:gestionar")`
- [x] 6.2 Test endpoint: usuario sin permiso `estructura:gestionar` → 403; usuario con permiso puede crear y listar carreras
- [x] 6.3 Triangular carreras: GET de carrera de otro tenant → 404; POST con código duplicado → 409; DELETE → soft delete (no aparece en listado)
- [x] 6.4 Agregar router de `cohortes`: mismos 5 endpoints con soporte de query param `carrera_id` en el listado
- [x] 6.5 Test + triangular cohortes: crear cohorte activa en carrera inactiva → 422; filtro por `carrera_id` funciona; aislamiento tenant
- [x] 6.6 Agregar router de `materias`: mismos 5 endpoints con soporte de query param `estado` en el listado
- [x] 6.7 Test + triangular materias: filtro por estado funciona; código duplicado → 409; aislamiento tenant
- [x] 6.8 Registrar los tres routers en `backend/app/api/v1/api.py` (o equivalente de registro de routers)

## 7. Cobertura y registro

- [x] 7.1 Ejecutar suite completa: `pytest backend/tests/ --cov=backend/app --cov-report=term-missing` — verificar ≥80% líneas en módulos nuevos y ≥90% cobertura de reglas de negocio (unicidad, estado, aislamiento tenant, regla carrera-inactiva)
- [x] 7.2 Actualizar `backend/app/models/__init__.py` y `backend/app/repositories/__init__.py` si no se hizo en pasos anteriores — confirmar que Alembic detecta los nuevos modelos con `alembic check`
- [x] 7.3 Marcar PA-01 y PA-07 como cerradas en `knowledge-base/10_preguntas_abiertas.md` con la resolución correspondiente (ADR-006 cierra PA-01; FK `carrera_id` en Cohorte cierra PA-07)
