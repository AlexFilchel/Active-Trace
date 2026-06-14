"""Async worker entrypoint for comunicaciones queue."""

import asyncio
import logging

from app.core.database import dispose_database, get_session_factory, initialize_database
from app.services.comunicaciones import CommunicationDispatchService, FakeCommunicationProvider


logger = logging.getLogger(__name__)


async def run_worker() -> None:
    initialize_database()
    session_factory = get_session_factory()
    logger.info("communication-worker-started")
    while True:
        async with session_factory() as session:
            service = CommunicationDispatchService(session=session, provider=FakeCommunicationProvider())
            processed = await service.process_pending(limit=50)
            await session.commit()
            logger.info("communication-worker-tick", extra={"processed": processed})
        await asyncio.sleep(1)


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("communication-worker-stopped")
    finally:
        asyncio.run(dispose_database())


if __name__ == "__main__":
    main()
