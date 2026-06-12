from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models import Asignacion, Carrera, Cohorte, Materia, Rol, Usuario
from app.repositories.usuarios import AsignacionRepository, UsuarioRepository
from tests.usuarios_test_utils import tenant_session


@pytest.fixture
async def usuarios_repo_session(valid_env):
    async for item in tenant_session():
        yield item


@pytest.mark.asyncio
async def test_usuario_repository_filters_by_tenant_and_email_hash(usuarios_repo_session):
    session, tenant_a, tenant_b = usuarios_repo_session

    usuario_a = Usuario(tenant_id=tenant_a.id, nombre="Ada", apellidos="Lovelace", email_encrypted="enc-a", email_hash="hash-a")
    usuario_b = Usuario(tenant_id=tenant_b.id, nombre="Grace", apellidos="Hopper", email_encrypted="enc-b", email_hash="hash-a")
    session.add_all([usuario_a, usuario_b])
    await session.commit()

    repo = UsuarioRepository(session=session, tenant_id=tenant_a.id)
    assert await repo.get_by_email_hash("hash-a") is not None
    assert len(await repo.list()) == 1
    assert await repo.get(usuario_b.id) is None


@pytest.mark.asyncio
async def test_usuario_repository_excludes_soft_deleted(usuarios_repo_session):
    session, tenant_a, _ = usuarios_repo_session

    repo = UsuarioRepository(session=session, tenant_id=tenant_a.id)
    usuario = await repo.create(nombre="Ada", apellidos="Lovelace", email_encrypted="enc-a", email_hash="hash-a")
    await repo.soft_delete(usuario.id)
    await session.commit()

    assert await repo.get(usuario.id) is None
    assert await repo.get(usuario.id, include_deleted=True) is not None


@pytest.mark.asyncio
async def test_asignacion_repository_filters_context_and_vigencia(usuarios_repo_session):
    session, tenant_a, tenant_b = usuarios_repo_session

    rol = Rol(tenant_id=tenant_a.id, nombre="COORDINADOR")
    carrera = Carrera(tenant_id=tenant_a.id, codigo="CAR", nombre="Carrera")
    session.add_all([rol, carrera])
    await session.flush()
    cohorte = Cohorte(tenant_id=tenant_a.id, carrera_id=carrera.id, nombre="2026", anio=2026, vig_desde=date(2026, 1, 1))
    materia = Materia(tenant_id=tenant_a.id, codigo="MAT", nombre="Materia")
    usuario = Usuario(tenant_id=tenant_a.id, nombre="Ada", apellidos="Lovelace", email_encrypted="enc-a", email_hash="hash-a")
    other_tenant_user = Usuario(tenant_id=tenant_b.id, nombre="Grace", apellidos="Hopper", email_encrypted="enc-b", email_hash="hash-b")
    session.add_all([cohorte, materia, usuario, other_tenant_user])
    await session.flush()

    vigente = Asignacion(
        tenant_id=tenant_a.id,
        usuario_id=usuario.id,
        rol_id=rol.id,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        desde=date.today() - timedelta(days=2),
        hasta=date.today() + timedelta(days=2),
    )
    vencida = Asignacion(
        tenant_id=tenant_a.id,
        usuario_id=usuario.id,
        rol_id=rol.id,
        desde=date.today() - timedelta(days=10),
        hasta=date.today() - timedelta(days=1),
    )
    session.add_all([vigente, vencida])
    await session.commit()

    repo = AsignacionRepository(session=session, tenant_id=tenant_a.id)
    assert len(await repo.list(usuario_id=usuario.id, materia_id=materia.id)) == 1
    assert len(await repo.list(usuario_id=usuario.id)) == 2
    assert len(await repo.list_vigentes_for_user(usuario.id)) == 1
    assert await repo.get(vigente.id) is not None
    assert await repo.get_by_usuario_and_rol(other_tenant_user.id, rol.id) == []
