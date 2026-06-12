from __future__ import annotations

from collections.abc import AsyncIterator
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_session_factory, initialize_database
from app.models import Tenant


async def ensure_schema() -> None:
    engine = initialize_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Apply additive column migrations for columns added after initial create_all
        _ADDITIVE_COLUMNS = [
            "ALTER TABLE tenant ADD COLUMN IF NOT EXISTS moodle_ws_url VARCHAR(500)",
            "ALTER TABLE tenant ADD COLUMN IF NOT EXISTS moodle_ws_token_encrypted VARCHAR(512)",
        ]
        for stmt in _ADDITIVE_COLUMNS:
            await conn.execute(text(stmt))


async def clean_database(session: AsyncSession) -> None:
    # TRUNCATE bypasses row-level triggers (e.g. audit_log's append-only trigger)
    # CASCADE handles FK dependencies automatically
    table_names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    await session.commit()


async def tenant_session() -> AsyncIterator[tuple[AsyncSession, Tenant, Tenant]]:
    await ensure_schema()
    session_factory = get_session_factory()

    async with session_factory() as session:
        await clean_database(session)
        tenant_a = Tenant(name="Tenant A", slug=f"tenant-a-{uuid.uuid4()}")
        tenant_b = Tenant(name="Tenant B", slug=f"tenant-b-{uuid.uuid4()}")
        session.add_all([tenant_a, tenant_b])
        await session.commit()
        yield session, tenant_a, tenant_b
        await clean_database(session)
