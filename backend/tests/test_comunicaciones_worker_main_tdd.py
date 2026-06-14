from __future__ import annotations

import asyncio

import pytest

from app.core.database import get_session_factory
from tests.usuarios_test_utils import ensure_schema


class _StopWorker(Exception):
    pass


@pytest.mark.asyncio
async def test_run_worker_usa_fake_provider_y_commit(monkeypatch: pytest.MonkeyPatch, valid_env):
    from app.services.comunicaciones import FakeCommunicationProvider
    from app.workers import main as worker_main

    await ensure_schema()
    session_factory = get_session_factory()
    captured: dict[str, object] = {"processed": None, "provider_type": None}

    class FakeDispatchService:
        def __init__(self, *, session, provider, max_retries: int = 2) -> None:
            captured["provider_type"] = type(provider)

        async def process_pending(self, *, limit: int = 50) -> int:
            captured["processed"] = limit
            return 7

    async def stop_sleep(_: int) -> None:
        raise _StopWorker

    monkeypatch.setattr(worker_main, "initialize_database", lambda: None)
    monkeypatch.setattr(worker_main, "get_session_factory", lambda: session_factory)
    monkeypatch.setattr(worker_main, "CommunicationDispatchService", FakeDispatchService)
    monkeypatch.setattr(worker_main.asyncio, "sleep", stop_sleep)

    with pytest.raises(_StopWorker):
        await worker_main.run_worker()

    assert captured["processed"] == 50
    assert captured["provider_type"] is FakeCommunicationProvider


def test_main_dispone_db_en_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch):
    from app.workers import main as worker_main

    captured: list[object] = []

    async def fake_dispose() -> None:
        captured.append("disposed")

    def fake_run(coro):
        if getattr(coro, "cr_code", None) and coro.cr_code.co_name == "run_worker":
            coro.close()
            raise KeyboardInterrupt
        captured.append("dispose-called")
        coro.close()
        return None

    monkeypatch.setattr(worker_main, "dispose_database", fake_dispose)
    monkeypatch.setattr(worker_main.asyncio, "run", fake_run)

    worker_main.main()

    assert captured == ["dispose-called"]
