## Context

C-01/C-02/C-03 establecieron la infraestructura, el multi-tenancy row-level y el sistema de autenticación JWT. El JWT emite un claim `roles: list[str]` con los nombres de los roles del usuario. Sin embargo, no existe ningún mecanismo que traduzca esos roles en permisos concretos ni que proteja los endpoints con un guard declarativo.

`app/core/permissions.py` es hoy un stub de una línea. `dependencies.py` expone `get_current_user` pero no tiene `require_permission`. Todos los routers futuros (C-05 en adelante) necesitan este guard para declarar qué permiso exigen.

**Constraint clave**: los permisos NO se almacenan en el JWT. Se resuelven server-side en cada petición consultando la DB, a partir de los nombres de rol del claim.

---

## Goals / Non-Goals

**Goals:**
- Definir tablas `Rol`, `Permiso`, `RolPermiso` como catálogo administrable por tenant.
- Proporcionar `require_permission("modulo:accion")` como dependencia FastAPI declarativa y fail-closed.
- Sembrar los 7 roles del dominio y la matriz base de `03_actores_y_roles.md §3.3` en la migración.
- Hacer la resolución de permisos server-side (unión de roles del JWT → consulta DB → permisos efectivos).

**Non-Goals:**
- Caché de permisos en memoria o Redis (se puede agregar si los benchmarks lo justifican; por ahora simple y correcto).
- Endpoints de ABM de roles/permisos (API administrativa — se agrega en C-06/C-07 junto a la gestión de usuarios).
- Impersonación (C-05 audit-log lo agrega después).
- Vigencia temporal de asignaciones (C-07 lo introduce; por ahora se resuelve desde el JWT directamente).

---

## Decisions

### D1 — Resolución de permisos: DB query por request, sin caché

**Decisión**: en cada request con `require_permission`, se ejecuta un query a la DB:
```sql
SELECT p.nombre FROM permiso p
JOIN rol_permiso rp ON rp.permiso_id = p.id
JOIN rol r ON r.id = rp.rol_id
WHERE r.nombre = ANY(:role_names)
  AND r.tenant_id = :tenant_id
  AND r.deleted_at IS NULL
  AND p.deleted_at IS NULL
```
y se verifica si el permiso requerido está en el resultado.

**Alternativa descartada**: almacenar los permisos en el JWT claim. Descartada porque los claims del token no se pueden revocar sin invalidar todas las sesiones, y la matriz de permisos es administrable (puede cambiar).

**Alternativa descartada**: caché en memoria por `(tenant_id, roles)`. Descartada por ahora: introduce invalidación de caché, complejidad extra, y los permisos de auth son consultas simples de lookup. Si los benchmarks lo justifican, se agrega en un change de optimización.

**Trade-off aceptado**: 1 query extra por cada endpoint protegido. Aceptable dado que es un JOIN simple con PKs indexadas y el volumen de usuarios/permisos es pequeño por tenant.

---

### D2 — `require_permission` como función que devuelve un Depends

**Decisión**:
```python
def require_permission(permission: str) -> Depends:
    async def _guard(
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedUser:
        ...check...
        return current_user
    return Depends(_guard)
```

Uso en router:
```python
@router.get("/calificaciones", dependencies=[require_permission("calificaciones:importar")])
```
o para acceder al usuario en la función:
```python
async def endpoint(user: AuthenticatedUser = require_permission("calificaciones:importar")):
```

**Alternativa descartada**: decorador de función. FastAPI maneja mejor la inyección de dependencias con `Depends`; el patrón de función-que-retorna-Depends es idiomático.

---

### D3 — `AuthenticatedUser` no cambia su contrato público

**Decisión**: `AuthenticatedUser` sigue siendo un dataclass con `user_id`, `tenant_id`, `roles: list[str]`, `email`. NO se le agrega `permissions` al dataclass. La verificación ocurre dentro del guard `require_permission` antes de llegar al handler.

**Razón**: añadir `permissions` al dataclass implicaría hacer el query en `get_current_user` (siempre, aunque el endpoint no lo necesite). Mejor hacerlo solo cuando el guard lo pide.

---

### D4 — Roles per-tenant con seed global replicado

**Decisión**: las tablas `Rol` y `Permiso` tienen `tenant_id`, permitiendo que un tenant tenga roles/permisos propios. La migración `003_rbac` siembra los 7 roles base y la matriz §3.3 para **todos los tenants existentes** usando `INSERT INTO rol SELECT ... FROM tenant`.

**Implicación**: cuando se crea un nuevo tenant (C-02/future), se deben crear también sus roles y permisos base. Esto se resuelve en el `TenantService` (C-07) o en el servicio de provisioning del tenant. Se documenta como deuda técnica en `10_preguntas_abiertas.md` si no está ya contemplado.

---

### D5 — Nombres de permisos: `modulo:accion` como strings libres

**Decisión**: los permisos son strings en formato `modulo:accion` (ej. `calificaciones:importar`, `equipos:asignar`). Se almacenan en la tabla `Permiso` como `nombre VARCHAR(64)`. No hay enum en código — el catálogo es la fuente de verdad.

**Razón**: lista hardcodeada en código requeriría un deploy para cada nuevo permiso. La base de datos permite evolución sin redeployar.

---

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| Un typo en el string del permiso en un router pasa desapercibido hasta runtime | Tests de integración que verifican que el permiso existe en DB. Los tests de roles/permisos de C-04 cubren esto con aserciones contra el seed. |
| La migración de seed puede fallar si hay tenants existentes en producción | El seed usa `INSERT ... ON CONFLICT DO NOTHING` para ser idempotente. La migración es segura de re-ejecutar. |
| Query extra por cada request protegido puede crecer con el número de endpoints | Aceptado como deuda técnica; se agrega caché en un change de optimización si los benchmarks lo justifican. Los JOINs son sobre PKs indexadas. |
| Roles del JWT desincronizados con `AuthUser.roles` en DB | El JWT tiene TTL de 15min. En caso de cambio de roles, el próximo refresh emite un token actualizado. Es el mismo trade-off que todo sistema JWT. |

---

## Migration Plan

1. `003_rbac.py`: crea tablas `rol`, `permiso`, `rol_permiso`.
2. Seed inline en `upgrade()`: inserta los 7 roles y la matriz de permisos para cada tenant existente.
3. Seed es idempotente (`INSERT ... ON CONFLICT DO NOTHING`) para soportar re-runs seguros.
4. `downgrade()`: hace DROP TABLE en orden inverso (respeta FK).
5. No hay rollback de datos de aplicación: los roles del JWT siguen siendo válidos durante el rollback (los endpoints perderían el guard, degradación aceptable para un rollback de emergencia).

---

## Open Questions

_(ninguna — la KB cubre todos los aspectos de C-04 necesarios para implementación)_
