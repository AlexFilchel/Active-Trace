"""Placeholder worker entrypoint reserved for ADR-003 queue implementation."""

import asyncio
import logging


async def run_worker() -> None:
    logging.getLogger(__name__).info("worker-placeholder-started")
    await asyncio.Event().wait()


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("worker-placeholder-stopped")


if __name__ == "__main__":
    main()
