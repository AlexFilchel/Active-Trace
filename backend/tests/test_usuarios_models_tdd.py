from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Asignacion, AuthUser, Carrera, Cohorte, Materia, Rol, Usuario
from app.models.base import utc_now
from tests.usuarios_test_utils import tenant_session


@pytest.fixture
async def usuarios_model_session(valid_env):
    async for item in tenant_session():
        yield item


@pytest.mark.asyncio
async def test_usuario_defaults_soft_delete_and_tenant_isolation(usuarios_model_session):
    session, tenant_a, tenant_b = usuarios_model_session

    usuario_a = Usuario(
        tenant_id=tenant_a.id,
        nombre="Ada",
        apellidos="Lovelace",
        email_encrypted="enc-a",
        email_hash="hash-a",
    )
    usuario_b = Usuario(
        tenant_id=tenant_b.id,
        nombre="Grace",
        apellidos="Hopper",
        email_encrypted="enc-b",
        email_hash="hash-a",
    )
    session.add_all([usuario_a, usuario_b])
    await session.commit()

    assert usuario_a.estado == "Activo"
    usuario_a.deleted_at = utc_now()
    await session.commit()

    persisted = await session.scalar(select(Usuario).where(Usuario.id == usuario_a.id))
    assert persisted is not None
    assert persisted.deleted_at is not None
    assert usuario_a.tenant_id != usuario_b.tenant_id


@pytest.mark.asyncio
async def test_usuario_email_hash_unique_per_tenant(usuarios_model_session):
    session, tenant_a, tenant_b = usuarios_model_session
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id

    session.add(
        Usuario(
            tenant_id=tenant_a.id,
            nombre="Ada",
            apellidos="Lovelace",
            email_encrypted="enc-a",
            email_hash="same-hash",
        )
    )
    await session.flush()

    session.add(
        Usuario(
            tenant_id=tenant_a.id,
            nombre="Otra",
            apellidos="Persona",
            email_encrypted="enc-b",
            email_hash="same-hash",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()

    session.add_all(
        [
            Usuario(
                tenant_id=tenant_a_id,
                nombre="Ada",
                apellidos="Lovelace",
                email_encrypted="enc-a2",
                email_hash="hash-x",
            ),
            Usuario(
                tenant_id=tenant_b_id,
                nombre="Grace",
                apellidos="Hopper",
                email_encrypted="enc-b2",
                email_hash="hash-x",
            ),
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_usuario_legajo_unique_per_tenant_only_when_present(usuarios_model_session):
    session, tenant_a, tenant_b = usuarios_model_session
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id

    session.add(
        Usuario(
            tenant_id=tenant_a.id,
            nombre="Ada",
            apellidos="Lovelace",
            email_encrypted="enc-a",
            email_hash="hash-a",
            legajo="LEG-001",
        )
    )
    await session.flush()

    session.add(
        Usuario(
            tenant_id=tenant_a.id,
            nombre="Otra",
            apellidos="Persona",
            email_encrypted="enc-b",
            email_hash="hash-b",
            legajo="LEG-001",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()

    session.add_all(
        [
            Usuario(
                tenant_id=tenant_a_id,
                nombre="Sin",
                apellidos="Legajo",
                email_encrypted="enc-c",
                email_hash="hash-c",
                legajo=None,
            ),
            Usuario(
                tenant_id=tenant_a_id,
                nombre="Sin",
                apellidos="Legajo Dos",
                email_encrypted="enc-d",
                email_hash="hash-d",
                legajo=None,
            ),
            Usuario(
                tenant_id=tenant_b_id,
                nombre="Tenant B",
                apellidos="Replica",
                email_encrypted="enc-e",
                email_hash="hash-e",
                legajo="LEG-001",
            ),
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_asignacion_model_context_and_vigencia(usuarios_model_session):
    session, tenant_a, _ = usuarios_model_session

    auth_user = AuthUser(tenant_id=tenant_a.id, email="auth@test.local", password_hash="hash", roles=["ADMIN"])
    rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
    carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR", nombre="Carrera")
    session.add_all([auth_user, rol, carrera])
    await session.flush()

    cohorte = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
    materia = Materia(tenant_id=tenant_a.id, codigo="MAT", nombre="Materia")
    responsable = Usuario(
        tenant_id=tenant_a.id,
        auth_user_id=auth_user.id,
        nombre="Resp",
        apellidos="Onsable",
        email_encrypted="enc-resp",
        email_hash="hash-resp",
    )
    asignado = Usuario(
        tenant_id=tenant_a.id,
        nombre="Asig",
        apellidos="Nado",
        email_encrypted="enc-asig",
        email_hash="hash-asig",
    )
    session.add_all([cohorte, materia, responsable, asignado])
    await session.flush()

    asignacion = Asignacion(
        tenant_id=tenant_a.id,
        usuario_id=asignado.id,
        rol_id=rol.id,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        responsable_id=responsable.id,
        comisiones=["A", "B"],
        desde=date.today(),
    )
    session.add(asignacion)
    await session.commit()

    assert asignacion.estado_vigencia == "Vigente"
    asignacion.deleted_at = utc_now()
    await session.commit()
    assert asignacion.deleted_at is not None
