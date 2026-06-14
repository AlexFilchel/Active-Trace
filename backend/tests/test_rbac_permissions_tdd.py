"""TDD tests for RBAC permission resolution (get_user_permissions).

Covers:
- Usuario con un rol resuelve sus permisos correctamente
- Usuario con múltiples roles recibe la unión de permisos (sin duplicados)
- Usuario sin roles tiene conjunto de permisos vacío
- Permisos de tenant A no se filtran en tenant B (aislamiento multi-tenant)
"""
from __future__ import annotations

from datetime import date
import pytest

from app.core.database import get_session_factory, initialize_database
from app.core.security import encrypt_value, hash_password
from app.core.permissions import get_user_permissions
from app.models import Asignacion, AuthLoginChallenge, AuthPasswordResetToken, AuthRefreshSession, AuthTotpCredential, AuthUser, Carrera, Cohorte, Materia, Permiso, Rol, RolPermiso, Tenant, Usuario
from tests.usuarios_test_utils import clean_database, ensure_schema


@pytest.fixture
async def permissions_db_session(valid_env):
    initialize_database()
    await ensure_schema()

    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)

        tenant_a = Tenant(name="Permissions Tenant A", slug="perms-tenant-a")
        tenant_b = Tenant(name="Permissions Tenant B", slug="perms-tenant-b")
        session.add_all([tenant_a, tenant_b])
        await session.commit()

        # Tenant A roles and permissions
        rol_profesor_a = Rol(tenant_id=tenant_a.id, nombre="PROFESOR")
        rol_coordinador_a = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
        session.add_all([rol_profesor_a, rol_coordinador_a])
        await session.flush()

        p_importar = Permiso(tenant_id=tenant_a.id, nombre="calificaciones:importar")
        p_comunicar = Permiso(tenant_id=tenant_a.id, nombre="comunicacion:enviar")
        p_equipos = Permiso(tenant_id=tenant_a.id, nombre="equipos:gestionar")
        session.add_all([p_importar, p_comunicar, p_equipos])
        await session.flush()

        # PROFESOR gets: calificaciones:importar, comunicacion:enviar
        rp1 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_profesor_a.id, permiso_id=p_importar.id)
        rp2 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_profesor_a.id, permiso_id=p_comunicar.id)
        # COORDINADOR gets: comunicacion:enviar (overlap), equipos:gestionar
        rp3 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coordinador_a.id, permiso_id=p_comunicar.id)
        rp4 = RolPermiso(tenant_id=tenant_a.id, rol_id=rol_coordinador_a.id, permiso_id=p_equipos.id)
        session.add_all([rp1, rp2, rp3, rp4])
        await session.commit()

        # Tenant B — different rol/permiso set
        rol_admin_b = Rol(tenant_id=tenant_b.id, nombre="ADMIN")
        session.add(rol_admin_b)
        await session.flush()
        p_admin_b = Permiso(tenant_id=tenant_b.id, nombre="tenant:configurar")
        session.add(p_admin_b)
        await session.flush()
        rp_b = RolPermiso(tenant_id=tenant_b.id, rol_id=rol_admin_b.id, permiso_id=p_admin_b.id)
        session.add(rp_b)
        await session.commit()

        yield session, tenant_a, tenant_b


@pytest.mark.asyncio
async def test_usuario_con_un_rol_resuelve_sus_permisos(permissions_db_session):
    """Usuario con rol PROFESOR resuelve exactamente sus permisos asignados."""
    session, tenant_a, _tenant_b = permissions_db_session

    permisos = await get_user_permissions(["PROFESOR"], tenant_a.id, session)

    assert permisos == {"calificaciones:importar", "comunicacion:enviar"}


@pytest.mark.asyncio
async def test_usuario_con_multiples_roles_recibe_union_sin_duplicados(permissions_db_session):
    """Usuario con PROFESOR + COORDINADOR recibe la unión de permisos (sin duplicados)."""
    session, tenant_a, _tenant_b = permissions_db_session

    permisos = await get_user_permissions(["PROFESOR", "COORDINADOR"], tenant_a.id, session)

    assert permisos == {"calificaciones:importar", "comunicacion:enviar", "equipos:gestionar"}
    # comunicacion:enviar is in both roles but appears once
    assert len(permisos) == 3


@pytest.mark.asyncio
async def test_usuario_sin_roles_tiene_permisos_vacios(permissions_db_session):
    """Usuario con roles=[] tiene conjunto de permisos vacío."""
    session, tenant_a, _tenant_b = permissions_db_session

    permisos = await get_user_permissions([], tenant_a.id, session)

    assert permisos == set()


@pytest.mark.asyncio
async def test_permisos_de_tenant_a_no_se_filtran_en_tenant_b(permissions_db_session):
    """Los roles de tenant A no otorgan permisos en tenant B."""
    session, tenant_a, tenant_b = permissions_db_session

    # PROFESOR exists in tenant A but NOT in tenant B
    permisos_b = await get_user_permissions(["PROFESOR"], tenant_b.id, session)

    assert permisos_b == set()

    # ADMIN exists in tenant B — its permissions should be from tenant B only
    permisos_admin_b = await get_user_permissions(["ADMIN"], tenant_b.id, session)
    assert permisos_admin_b == {"tenant:configurar"}

    # Same rol name ADMIN queried against tenant A returns empty (no ADMIN in tenant A fixture)
    permisos_admin_a = await get_user_permissions(["ADMIN"], tenant_a.id, session)
    assert permisos_admin_a == set()


@pytest.mark.asyncio
async def test_usuario_con_asignacion_activa_suma_permiso(permissions_db_session):
    session, tenant_a, _tenant_b = permissions_db_session

    auth_user = AuthUser(
        tenant_id=tenant_a.id,
        email="docente@tenant-a.local",
        password_hash=hash_password("P1!"),
        roles=[],
    )
    rol_tutor = Rol(tenant_id=tenant_a.id, nombre="TUTOR_ASIGNADO")
    permiso_tutor = Permiso(tenant_id=tenant_a.id, nombre="comunicacion:aprobar")
    carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR-RBAC-A", nombre="Carrera RBAC")
    materia = Materia(tenant_id=tenant_a.id, codigo="MAT-RBAC-A", nombre="Materia RBAC")
    session.add_all([auth_user, rol_tutor, permiso_tutor, carrera, materia])
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tenant_a.id,
        carrera_id=carrera.id,
        nombre="2026",
        anio=2026,
        vig_desde=date(2026, 1, 1),
    )
    session.add(cohorte)
    await session.flush()

    usuario = Usuario(
        tenant_id=tenant_a.id,
        auth_user_id=auth_user.id,
        nombre="Docente",
        apellidos="Asignado",
        email_encrypted=encrypt_value("docente@tenant-a.local"),
        email_hash="hash-docente-a",
    )
    session.add(usuario)
    await session.flush()

    session.add_all([
        RolPermiso(tenant_id=tenant_a.id, rol_id=rol_tutor.id, permiso_id=permiso_tutor.id),
        Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario.id,
            rol_id=rol_tutor.id,
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            desde=date.today(),
            hasta=None,
            comisiones=["A"],
        ),
    ])
    await session.commit()

    permisos = await get_user_permissions([], tenant_a.id, session, auth_user_id=auth_user.id)

    assert permisos == {"comunicacion:aprobar"}


@pytest.mark.asyncio
async def test_resolucion_repetida_de_asignaciones_permanece_estable(permissions_db_session):
    session, tenant_a, _tenant_b = permissions_db_session

    auth_user = AuthUser(
        tenant_id=tenant_a.id,
        email="coord@tenant-a.local",
        password_hash=hash_password("P1!"),
        roles=["COORDINADOR"],
    )
    rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR_ASIGNADO")
    permiso = Permiso(tenant_id=tenant_a.id, nombre="comunicacion:monitorear")
    carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR-RBAC-B", nombre="Carrera RBAC B")
    materia = Materia(tenant_id=tenant_a.id, codigo="MAT-RBAC-B", nombre="Materia RBAC B")
    session.add_all([auth_user, rol, permiso, carrera, materia])
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tenant_a.id,
        carrera_id=carrera.id,
        nombre="2027",
        anio=2027,
        vig_desde=date(2027, 1, 1),
    )
    session.add(cohorte)
    await session.flush()

    usuario = Usuario(
        tenant_id=tenant_a.id,
        auth_user_id=auth_user.id,
        nombre="Coord",
        apellidos="Activo",
        email_encrypted=encrypt_value("coord@tenant-a.local"),
        email_hash="hash-coord-a",
    )
    session.add(usuario)
    await session.flush()

    session.add_all([
        RolPermiso(tenant_id=tenant_a.id, rol_id=rol.id, permiso_id=permiso.id),
        Asignacion(
            tenant_id=tenant_a.id,
            usuario_id=usuario.id,
            rol_id=rol.id,
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            desde=date.today(),
            hasta=None,
            comisiones=["B"],
        ),
    ])
    await session.commit()

    for _ in range(5):
        permisos = await get_user_permissions([], tenant_a.id, session, auth_user_id=auth_user.id)
        assert permisos == {"comunicacion:monitorear"}
