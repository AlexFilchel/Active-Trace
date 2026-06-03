import asyncio
import uuid

import pytest
from sqlalchemy import String, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, get_session_factory, initialize_database


from app.models import Tenant, TenantScopedMixin


class SampleTenantRecord(TenantScopedMixin, Base):
    __tablename__ = "test_sample_tenant_record"
    __table_args__ = {"extend_existing": True}

    name: Mapped[str] = mapped_column(String(100), nullable=False)


@pytest.fixture
async def tenant_db_session(valid_env):
    engine = initialize_database()

    async with engine.begin() as connection:
        await connection.run_sync(Tenant.__table__.create, checkfirst=True)
        await connection.run_sync(SampleTenantRecord.__table__.create, checkfirst=True)

    session_factory = get_session_factory()

    async with session_factory() as session:
        await session.execute(delete(SampleTenantRecord))
        await session.execute(delete(Tenant))
        await session.commit()

        yield session

        await session.execute(delete(SampleTenantRecord))
        await session.execute(delete(Tenant))
        await session.commit()


@pytest.mark.asyncio
async def test_tenant_root_persists_uuid_and_lifecycle(tenant_db_session):
    tenant = Tenant(name="Universidad Uno", slug="universidad-uno")

    tenant_db_session.add(tenant)
    await tenant_db_session.commit()
    await tenant_db_session.refresh(tenant)

    assert isinstance(tenant.id, uuid.UUID)
    assert tenant.created_at is not None
    assert tenant.updated_at is not None
    assert tenant.deleted_at is None


@pytest.mark.asyncio
async def test_tenant_scoped_mixin_provides_standard_fields_and_foreign_key(tenant_db_session):
    tenant = Tenant(name="Universidad Dos", slug="universidad-dos")
    tenant_db_session.add(tenant)
    await tenant_db_session.flush()

    record = SampleTenantRecord(name="registro", tenant_id=tenant.id)
    tenant_db_session.add(record)
    await tenant_db_session.commit()

    persisted = await tenant_db_session.scalar(select(SampleTenantRecord).where(SampleTenantRecord.id == record.id))

    assert persisted is not None
    assert persisted.tenant_id == tenant.id
    assert persisted.created_at is not None
    assert persisted.updated_at is not None
    assert persisted.deleted_at is None
    foreign_key_targets = {foreign_key.target_fullname for foreign_key in SampleTenantRecord.__table__.c.tenant_id.foreign_keys}

    assert foreign_key_targets == {"tenant.id"}


@pytest.mark.asyncio
async def test_updated_at_changes_without_mutating_created_at(tenant_db_session):
    tenant = Tenant(name="Universidad Tres", slug="universidad-tres")
    tenant_db_session.add(tenant)
    await tenant_db_session.flush()

    record = SampleTenantRecord(name="antes", tenant_id=tenant.id)
    tenant_db_session.add(record)
    await tenant_db_session.commit()
    await tenant_db_session.refresh(record)

    created_at = record.created_at
    updated_at = record.updated_at

    await asyncio.sleep(0.01)
    record.name = "despues"
    await tenant_db_session.commit()
    await tenant_db_session.refresh(record)

    assert record.created_at == created_at
    assert record.updated_at > updated_at


@pytest.mark.asyncio
async def test_soft_delete_marks_deleted_at_without_removing_row(tenant_db_session):
    tenant = Tenant(name="Universidad Cuatro", slug="universidad-cuatro")
    tenant_db_session.add(tenant)
    await tenant_db_session.flush()

    record = SampleTenantRecord(name="persistente", tenant_id=tenant.id)
    tenant_db_session.add(record)
    await tenant_db_session.commit()

    record.deleted_at = record.updated_at
    await tenant_db_session.commit()

    persisted = await tenant_db_session.scalar(select(SampleTenantRecord).where(SampleTenantRecord.id == record.id))

    assert persisted is not None
    assert persisted.deleted_at is not None
