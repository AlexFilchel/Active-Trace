"""Seed de datos mínimos para desarrollo local.

Crea:
  - Tenant
  - Roles + Permisos base
  - AuthUser admin con todos los roles
  - AuthUser profesor
  - Usuario perfil para cada auth_user
  - Carrera, Cohorte, Materia de ejemplo
  - Asignacion (admin a la materia)

Uso: python seed_dev_data.py
"""

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")


async def main():
    from app.core.config import get_settings
    from app.core.database import get_session_factory, initialize_database
    from app.core.security import hash_password
    from app.models import (
        Asignacion,
        AuthUser,
        Carrera,
        Cohorte,
        Materia,
        Permiso,
        Rol,
        RolPermiso,
        Tenant,
        Usuario,
    )
    from app.models.base import utc_now
    from app.services.auth import utc_now as auth_utc_now

    settings = get_settings()
    initialize_database()
    factory = get_session_factory()

    async with factory() as session:
        # ── 1. Tenant ──
        print("Creando tenant...")
        tenant = Tenant(
            name="Demo University",
            slug="demo",
            status="active",
        )
        session.add(tenant)
        await session.flush()
        tenant_id = tenant.id
        print(f"  -> Tenant ID: {tenant_id}")

        # ── 2. Roles del dominio ──
        print("Creando roles...")
        roles_data = [
            ("ALUMNO", "Estudiante que cursa materias"),
            ("TUTOR", "Auxiliar / ayudante de cátedra"),
            ("PROFESOR", "Docente a cargo de una o más comisiones"),
            ("COORDINADOR", "Responsable de un conjunto de materias o cohorte"),
            ("NEXO", "Rol de articulación / enlace transversal"),
            ("ADMIN", "Administrador del sistema dentro del tenant"),
            ("FINANZAS", "Responsable de liquidaciones y honorarios"),
        ]
        roles = {}
        for nombre, desc in roles_data:
            r = Rol(tenant_id=tenant_id, nombre=nombre, descripcion=desc)
            session.add(r)
            roles[nombre] = r
        await session.flush()

        # ── 3. Permisos base ──
        print("Creando permisos...")
        permisos_list = [
            "estado_academico:ver_propio",
            "evaluacion:reservar_instancia",
            "avisos:confirmar",
            "calificaciones:importar",
            "atrasados:ver",
            "entregas:ver_sin_corregir",
            "comunicacion:enviar",
            "comunicacion:aprobar",
            "encuentros:gestionar",
            "guardias:registrar",
            "tareas:gestionar",
            "avisos:publicar",
            "equipos:gestionar",
            "estructura:gestionar",
            "usuarios:gestionar",
            "auditoria:ver",
            "liquidaciones:operar_grilla",
            "liquidaciones:cerrar",
            "facturas:gestionar",
            "tenant:configurar",
            "impersonacion:usar",
        ]
        permisos = {}
        for pnombre in permisos_list:
            p = Permiso(tenant_id=tenant_id, nombre=pnombre)
            session.add(p)
            permisos[pnombre] = p
        await session.flush()

        # ── 4. Asignar TODOS los permisos a ADMIN ──
        #     Y subsets a COORDINADOR y PROFESOR
        print("Asignando permisos a roles...")
        admin_rol = roles["ADMIN"]
        coord_rol = roles["COORDINADOR"]
        prof_rol = roles["PROFESOR"]

        # ADMIN → todos
        for p in permisos.values():
            session.add(RolPermiso(tenant_id=tenant_id, rol_id=admin_rol.id, permiso_id=p.id))

        # COORDINADOR → permisos de gestión
        coord_perms = [
            "calificaciones:importar",
            "atrasados:ver",
            "entregas:ver_sin_corregir",
            "comunicacion:enviar",
            "comunicacion:aprobar",
            "encuentros:gestionar",
            "guardias:registrar",
            "tareas:gestionar",
            "avisos:publicar",
            "equipos:gestionar",
        ]
        for pnombre in coord_perms:
            session.add(RolPermiso(tenant_id=tenant_id, rol_id=coord_rol.id, permiso_id=permisos[pnombre].id))

        # PROFESOR → permisos de cursada
        prof_perms = [
            "estado_academico:ver_propio",
            "calificaciones:importar",
            "atrasados:ver",
            "entregas:ver_sin_corregir",
            "comunicacion:enviar",
        ]
        for pnombre in prof_perms:
            session.add(RolPermiso(tenant_id=tenant_id, rol_id=prof_rol.id, permiso_id=permisos[pnombre].id))

        await session.flush()

        # ── 5. AuthUser admin ──
        print("Creando auth_user admin...")
        admin_user = AuthUser(
            tenant_id=tenant_id,
            email="admin@demo.com",
            password_hash=hash_password("admin123"),
            roles=["ADMIN", "COORDINADOR", "PROFESOR"],
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()
        admin_user_id = admin_user.id
        print(f"  -> Admin AuthUser ID: {admin_user_id}")

        # ── 6. AuthUser profesor ──
        print("Creando auth_user profesor...")
        prof_user = AuthUser(
            tenant_id=tenant_id,
            email="profesor@demo.com",
            password_hash=hash_password("prof123"),
            roles=["PROFESOR"],
            is_active=True,
        )
        session.add(prof_user)
        await session.flush()
        prof_user_id = prof_user.id
        print(f"  -> Profesor AuthUser ID: {prof_user_id}")

        # ── 7. Usuario (perfil PII) ──
        print("Creando perfiles de usuario...")
        from app.core.security import encrypt_value
        import hashlib

        def _hash_email(email: str) -> str:
            return hashlib.sha256(email.strip().lower().encode()).hexdigest()

        admin_perfil = Usuario(
            tenant_id=tenant_id,
            auth_user_id=admin_user_id,
            nombre="Admin",
            apellidos="Sistema",
            email_encrypted=encrypt_value("admin@demo.com"),
            email_hash=_hash_email("admin@demo.com"),
            dni_encrypted=encrypt_value("12345678"),
            estado="Activo",
        )
        session.add(admin_perfil)

        prof_perfil = Usuario(
            tenant_id=tenant_id,
            auth_user_id=prof_user_id,
            nombre="Carlos",
            apellidos="Lopez",
            email_encrypted=encrypt_value("profesor@demo.com"),
            email_hash=_hash_email("profesor@demo.com"),
            dni_encrypted=encrypt_value("87654321"),
            estado="Activo",
        )
        session.add(prof_perfil)
        await session.flush()

        # ── 8. Carrera ──
        print("Creando carrera, cohorte y materia...")
        carrera = Carrera(
            tenant_id=tenant_id,
            codigo="ING-SIS",
            nombre="Ingenieria en Sistemas",
            estado="Activa",
        )
        session.add(carrera)
        await session.flush()

        # ── 8b. Cohorte 2026 ──
        cohorte = Cohorte(
            tenant_id=tenant_id,
            carrera_id=carrera.id,
            nombre="2026",
            anio=2026,
            vig_desde=date(2026, 3, 1),
            estado="Activa",
        )
        session.add(cohorte)
        await session.flush()

        # ── 8c. Materia ──
        materia = Materia(
            tenant_id=tenant_id,
            codigo="ING-SIS-101",
            nombre="Algoritmos y Programacion I",
            estado="Activa",
        )
        session.add(materia)
        await session.flush()

        # ── 9. Asignacion admin a la materia ──
        print("Creando asignacion admin...")
        hoy = date.today()
        asignacion = Asignacion(
            tenant_id=tenant_id,
            usuario_id=admin_perfil.id,
            rol_id=admin_rol.id,
            materia_id=materia.id,
            carrera_id=carrera.id,
            cohorte_id=cohorte.id,
            desde=hoy - timedelta(days=30),
            hasta=hoy + timedelta(days=335),
        )
        session.add(asignacion)
        await session.flush()

        await session.commit()

        print()
        print("=" * 60)
        print("[OK] SEED COMPLETADO")
        print("=" * 60)
        print(f"  Tenant:          demo")
        print(f"  Admin email:     admin@demo.com")
        print(f"  Admin password:  admin123")
        print(f"  Profesor email:  profesor@demo.com")
        print(f"  Profesor pass:   prof123")
        print(f"  Carrera:         {carrera.nombre} (ID: {carrera.id})")
        print(f"  Cohorte:         {cohorte.nombre} (ID: {cohorte.id})")
        print(f"  Materia:         {materia.nombre} (ID: {materia.id})")
        print(f"  Admin perfil ID: {admin_perfil.id}")
        print(f"  Prof perfil ID:  {prof_perfil.id}")
        print("=" * 60)
        print()
        print("Ahora anda a http://localhost:8000/docs y:")
        print("  1. POST /api/auth/login -> { \"email\": \"admin@demo.com\", \"password\": \"admin123\" }")
        print("  2. Copia el access_token")
        print("  3. Arriba a la derecha, click 'Authorize' y pega: Bearer <token>")
        print("  4. Ya podes probar todos los endpoints")


if __name__ == "__main__":
    asyncio.run(main())
