from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.models import AuthUser, Carrera, Cohorte, Materia, Rol, Usuario
from app.services.usuarios import ConflictError, NotFoundError, UsuarioService
from tests.usuarios_test_utils import tenant_session


@pytest.fixture
async def usuarios_service_session(valid_env):
    async for item in tenant_session():
        yield item


@pytest.mark.asyncio
async def test_crear_usuario_encrypts_pii_and_rejects_duplicate_email(usuarios_service_session):
    session, tenant_a, _ = usuarios_service_session
    service = UsuarioService(session=session, tenant_id=tenant_a.id)

    usuario = await service.crear_usuario(
        nombre="Ada",
        apellidos="Lovelace",
        email="  ADA@Test.Local ",
        dni="12345678",
        cuil="20-12345678-9",
        cbu="1234567890123456789012",
        alias_cbu="ada.trace",
    )
    await session.commit()

    row = (
        await session.execute(
            text(
                "SELECT email_encrypted, email_hash, dni_encrypted, cuil_encrypted, cbu_encrypted, alias_cbu_encrypted "
                "FROM usuario WHERE id = :id"
            ),
            {"id": str(usuario.id)},
        )
    ).one()
    assert row.email_encrypted != "ada@test.local"
    assert row.dni_encrypted != "12345678"
    assert row.cuil_encrypted != "20-12345678-9"
    assert row.cbu_encrypted != "1234567890123456789012"
    assert row.alias_cbu_encrypted != "ada.trace"
    assert row.email_hash

    with pytest.raises(ConflictError):
        await service.crear_usuario(nombre="Otra", apellidos="Persona", email="ada@test.local")


@pytest.mark.asyncio
async def test_crear_asignacion_validates_same_tenant_and_historical_listing(usuarios_service_session):
    session, tenant_a, tenant_b = usuarios_service_session
    service = UsuarioService(session=session, tenant_id=tenant_a.id)

    auth_user = AuthUser(tenant_id=tenant_a.id, email="auth@test.local", password_hash="hash", roles=[])
    other_auth_user = AuthUser(tenant_id=tenant_b.id, email="other@test.local", password_hash="hash", roles=[])
    rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
    foreign_rol = Rol(tenant_id=tenant_b.id, nombre="COORDINADOR")
    carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR", nombre="Carrera")
    foreign_carrera = Carrera(tenant_id=tenant_b.id, codigo="CAR", nombre="Carrera B")
    session.add_all([auth_user, other_auth_user, rol, foreign_rol, carrera, foreign_carrera])
    await session.flush()
    foreign_usuario = Usuario(
        tenant_id=tenant_b.id,
        auth_user_id=other_auth_user.id,
        nombre="Grace",
        apellidos="Hopper",
        email_encrypted="enc-grace",
        email_hash="hash-grace",
    )
    cohorte = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
    foreign_cohorte = Cohorte(tenant_id=tenant_b.id, carrera_id=foreign_carrera.id, nombre="2027", anio=2027, vig_desde=date(2027, 1, 1))
    materia = Materia(tenant_id=tenant_a.id, codigo="MAT", nombre="Materia")
    foreign_materia = Materia(tenant_id=tenant_b.id, codigo="MAT-B", nombre="Materia B")
    session.add_all([foreign_usuario, cohorte, foreign_cohorte, materia, foreign_materia])
    await session.flush()

    usuario = await service.crear_usuario(nombre="Ada", apellidos="Lovelace", email="ada@test.local", auth_user_id=auth_user.id)
    responsable = await service.crear_usuario(nombre="Resp", apellidos="Onsable", email="resp@test.local")
    await session.commit()

    asignacion = await service.crear_asignacion(
        usuario_id=usuario.id,
        rol_id=rol.id,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        responsable_id=responsable.id,
        desde=date.today() - timedelta(days=2),
        hasta=date.today() - timedelta(days=1),
    )
    await session.commit()

    historicas = await service.listar_asignaciones(usuario_id=usuario.id)
    vigentes = await service.listar_asignaciones_vigentes_para_auth_user(auth_user.id)
    assert len(historicas) == 1
    assert historicas[0].estado_vigencia == "Vencida"
    assert vigentes == set()

    with pytest.raises(NotFoundError):
        await service.crear_asignacion(usuario_id=usuario.id, rol_id=foreign_rol.id, desde=date.today())

    with pytest.raises(NotFoundError):
        await service.crear_asignacion(usuario_id=usuario.id, rol_id=rol.id, carrera_id=foreign_carrera.id, desde=date.today())

    with pytest.raises(NotFoundError):
        await service.crear_asignacion(usuario_id=usuario.id, rol_id=rol.id, materia_id=foreign_materia.id, desde=date.today())

    with pytest.raises(NotFoundError):
        await service.crear_asignacion(usuario_id=usuario.id, rol_id=rol.id, cohorte_id=foreign_cohorte.id, desde=date.today())

    with pytest.raises(NotFoundError):
        await service.crear_asignacion(usuario_id=usuario.id, rol_id=rol.id, responsable_id=foreign_usuario.id, desde=date.today())
