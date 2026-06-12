import uuid

import pytest
from sqlalchemy import String, delete, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, get_session_factory, initialize_database
from app.models import Tenant, TenantScopedMixin
from app.repositories import TenantScopedRepository


class RepositoryRecord(TenantScopedMixin, Base):
    __tablename__ = "test_repository_record"
    __table_args__ = {"extend_existing": True}

    name: Mapped[str] = mapped_column(String(100), nullable=False)


@pytest.fixture
async def tenant_repository_session(valid_env):
    engine = initialize_database()

    async with engine.begin() as connection:
        await connection.run_sync(Tenant.__table__.create, checkfirst=True)
        await connection.run_sync(RepositoryRecord.__table__.create, checkfirst=True)
        # Ensure additive columns exist if tenant table was left in a downgraded state
        await connection.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS moodle_ws_url VARCHAR(500)"))
        await connection.execute(text("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS moodle_ws_token_encrypted VARCHAR(512)"))

    session_factory = get_session_factory()

    async with session_factory() as session:
        await session.execute(delete(RepositoryRecord))
        await session.execute(delete(Tenant))
        await session.commit()

        yield session

        await session.execute(delete(RepositoryRecord))
        await session.execute(delete(Tenant))
        await session.commit()


@pytest.mark.asyncio
async def test_repository_requires_tenant_context(tenant_repository_session):
    with pytest.raises(ValueError):
        TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=None)


@pytest.mark.asyncio
async def test_repository_default_queries_do_not_cross_tenants_or_return_deleted_rows(tenant_repository_session):
    tenant_a = Tenant(name="Tenant A", slug="tenant-a")
    tenant_b = Tenant(name="Tenant B", slug="tenant-b")
    tenant_repository_session.add_all([tenant_a, tenant_b])
    await tenant_repository_session.flush()

    repository_a = TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=tenant_a.id)
    await repository_a.create(name="visible")
    hidden = await repository_a.create(name="deleted")

    repository_b = TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=tenant_b.id)
    await repository_b.create(name="foreign")

    await repository_a.soft_delete(hidden.id)

    rows = await repository_a.list()

    assert len(rows) == 1
    assert rows[0].name == "visible"
    assert rows[0].tenant_id == tenant_a.id


@pytest.mark.asyncio
async def test_repository_include_deleted_is_opt_in_and_still_tenant_scoped(tenant_repository_session):
    tenant_a = Tenant(name="Tenant C", slug="tenant-c")
    tenant_b = Tenant(name="Tenant D", slug="tenant-d")
    tenant_repository_session.add_all([tenant_a, tenant_b])
    await tenant_repository_session.flush()

    repository_a = TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=tenant_a.id)
    deleted = await repository_a.create(name="deleted-visible-only-with-flag")
    repository_b = TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=tenant_b.id)
    await repository_b.create(name="foreign-deleted")
    await repository_a.soft_delete(deleted.id)
    await tenant_repository_session.commit()

    rows = await repository_a.list(include_deleted=True)

    assert len(rows) == 1
    assert rows[0].id == deleted.id
    assert rows[0].tenant_id == tenant_a.id
    assert rows[0].deleted_at is not None


@pytest.mark.asyncio
async def test_repository_update_is_restricted_to_current_tenant(tenant_repository_session):
    tenant_a = Tenant(name="Tenant E", slug="tenant-e")
    tenant_b = Tenant(name="Tenant F", slug="tenant-f")
    tenant_repository_session.add_all([tenant_a, tenant_b])
    await tenant_repository_session.flush()

    repository_a = TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=tenant_a.id)
    repository_b = TenantScopedRepository(session=tenant_repository_session, model=RepositoryRecord, tenant_id=tenant_b.id)
    foreign = await repository_b.create(name="foreign")
    await tenant_repository_session.commit()

    updated = await repository_a.update(foreign.id, name="mutated")
    await tenant_repository_session.commit()
    persisted = await repository_b.get(foreign.id, include_deleted=True)

    assert updated is None
    assert persisted is not None
    assert persisted.name == "foreign"
