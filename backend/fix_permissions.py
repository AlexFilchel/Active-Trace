"""Agrega permisos faltantes al tenant demo.

Los permisos que faltan vs lo que usa el código:
  - equipos:asignar  (usado por equipos.py y usuarios.py)
  - padron:gestionar (usado por padron.py)

La migracion 003_rbac tiene "equipos:gestionar" que NO usa ningun endpoint,
y NO tiene "equipos:asignar" ni "padron:gestionar".

Uso: python fix_permissions.py
"""

import asyncio
import sys
sys.path.insert(0, ".")


async def main():
    from app.core.config import get_settings
    from app.core.database import get_session_factory, initialize_database
    from app.models import Permiso, Rol, RolPermiso, Tenant

    settings = get_settings()
    initialize_database()
    factory = get_session_factory()

    async with factory() as session:
        # Buscar tenant demo
        tenant = await session.scalar(
            __import__("sqlalchemy").select(Tenant).where(Tenant.slug == "demo")
        )
        if not tenant:
            print("[ERROR] No existe tenant 'demo'. Ejecutá seed_dev_data.py primero.")
            return

        tenant_id = tenant.id
        print(f"Tenant: {tenant.slug} (ID: {tenant_id})")

        # Permisos que faltan
        missing = ["equipos:asignar", "padron:gestionar"]
        created_perms = {}

        for pnombre in missing:
            # Verificar si ya existe
            exists = await session.scalar(
                __import__("sqlalchemy").select(Permiso).where(
                    Permiso.tenant_id == tenant_id,
                    Permiso.nombre == pnombre,
                    Permiso.deleted_at.is_(None),
                )
            )
            if exists:
                print(f"  [OK] {pnombre} ya existe (ID: {exists.id})")
                created_perms[pnombre] = exists
            else:
                p = Permiso(tenant_id=tenant_id, nombre=pnombre)
                session.add(p)
                await session.flush()
                print(f"  [CREADO] {pnombre} (ID: {p.id})")
                created_perms[pnombre] = p

        # Asignar a ADMIN y COORDINADOR
        admin_rol = await session.scalar(
            __import__("sqlalchemy").select(Rol).where(
                Rol.tenant_id == tenant_id,
                Rol.nombre == "ADMIN",
                Rol.deleted_at.is_(None),
            )
        )
        coord_rol = await session.scalar(
            __import__("sqlalchemy").select(Rol).where(
                Rol.tenant_id == tenant_id,
                Rol.nombre == "COORDINADOR",
                Rol.deleted_at.is_(None),
            )
        )

        roles_asignar = {}
        if admin_rol:
            roles_asignar["ADMIN"] = admin_rol
        if coord_rol:
            roles_asignar["COORDINADOR"] = coord_rol

        for rol_nombre, rol in roles_asignar.items():
            for pnombre, p in created_perms.items():
                # Verificar si ya tiene el permiso asignado
                rp_exists = await session.scalar(
                    __import__("sqlalchemy").select(RolPermiso).where(
                        RolPermiso.tenant_id == tenant_id,
                        RolPermiso.rol_id == rol.id,
                        RolPermiso.permiso_id == p.id,
                        RolPermiso.deleted_at.is_(None),
                    )
                )
                if rp_exists:
                    print(f"  [OK] {rol_nombre} ya tiene {pnombre}")
                else:
                    session.add(RolPermiso(
                        tenant_id=tenant_id,
                        rol_id=rol.id,
                        permiso_id=p.id,
                    ))
                    print(f"  [ASIGNADO] {rol_nombre} -> {pnombre}")

        await session.commit()
        print()
        print("[OK] Permisos actualizados. Ahora proba de nuevo /api/equipos/mis-equipos")


if __name__ == "__main__":
    asyncio.run(main())
