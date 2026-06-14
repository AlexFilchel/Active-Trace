## 1. Safety Net y contratos (RED)

- [x] 1.1 Escribir tests de contrato para `/api/analisis/*` que fallen sin implementación: sesión requerida, `atrasados:ver`, DTOs con `extra='forbid'` y 403 fail-closed.
- [x] 1.2 Escribir tests de repositorio con DB real/efímera para tenant isolation y alcance por rol/asignación, sin mocks de DB.
- [x] 1.3 Escribir tests de servicio para RN-06: atrasado por actividad faltante y por nota inferior al umbral.
- [x] 1.4 Escribir tests de servicio para RN-09: ranking solo incluye alumnos con al menos una aprobada.
- [x] 1.5 Escribir tests de notas finales agrupadas, monitor con filtros y export de TPs sin corregir (RN-07/RN-08).

## 2. Estructura de módulo y DTOs (GREEN mínimo)

- [x] 2.1 Crear módulo backend `analisis` con routers, schemas, services y repositories siguiendo Routers → Services → Repositories → Models.
- [x] 2.2 Definir DTOs Pydantic v2 de filtros/respuestas/export con `ConfigDict(extra='forbid')`.
- [x] 2.3 Registrar rutas `/api/analisis/*` con `require_permission("atrasados:ver")` y contexto de identidad solo desde sesión JWT.

## 3. Repositories tenant-scoped

- [x] 3.1 Implementar consultas para padrón activo, calificaciones, umbral vigente y asignaciones autorizadas con filtro `tenant_id` obligatorio.
- [x] 3.2 Implementar datasets para atrasados, ranking, resúmenes, notas finales, monitor y TPs sin corregir sin lógica RN en SQL más allá de filtros/joins necesarios.
- [x] 3.3 Agregar paginación/límites y orden estable en monitores y ranking.

## 4. Services de análisis

- [x] 4.1 Implementar cómputo RN-06 con motivos trazables por alumno/actividad.
- [x] 4.2 Implementar ranking RN-09 descendente y exclusión de alumnos sin aprobadas.
- [x] 4.3 Implementar resumen rápido por materia y notas finales agrupadas con agregación determinística documentada.
- [x] 4.4 Implementar monitor general y monitor por rol con filtros de materia, regional, comisión, búsqueda, estado, criterio y fechas para coordinación/admin.
- [x] 4.5 Implementar export de TPs sin corregir reutilizando el caso de uso RN-07/RN-08.

## 5. Triangulación, refactor y evidencia final

- [x] 5.1 Triangular tests con casos borde: sin datos, sin actividades seleccionadas/importadas, umbral por defecto, umbral explícito y alumno sin cuenta de usuario.
- [x] 5.2 Refactorizar para mantener archivos backend ≤500 LOC y separar helpers puros testeables si hace falta.
- [x] 5.3 Verificar que no haya SQL en Services, ni DB directa fuera de Repositories, ni tenant/user identity desde request params/body/headers.
- [x] 5.4 Ejecutar suite relevante con cobertura de reglas de negocio y documentar evidencia RED→GREEN→TRIANGULATE→REFACTOR en el resumen de apply.

> Nota de apply correctivo: RN-07 ya usa señal persistida `finalizacion_actividad` (finalizado + escala textual) para exportar solo entregas finalizadas sin calificación registrada; se eliminó el fallback por "actividad textual faltante".
