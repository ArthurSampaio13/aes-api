from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from src.infrastructure import app_factory


async def test_lifespan_starts_and_stops_the_broker(monkeypatch):
    broker = AsyncMock()
    monkeypatch.setattr(app_factory, "default_broker", broker)

    lifespan = app_factory.lifespan_factory(SimpleNamespace(), create_tables_on_startup=False)
    async with lifespan(FastAPI()):
        broker.startup.assert_awaited_once()
        broker.shutdown.assert_not_awaited()

    broker.shutdown.assert_awaited_once()


async def test_lifespan_shuts_down_broker_even_if_startup_fails(monkeypatch):
    broker = AsyncMock()
    broker.startup.side_effect = RuntimeError("boom")
    monkeypatch.setattr(app_factory, "default_broker", broker)

    lifespan = app_factory.lifespan_factory(SimpleNamespace(), create_tables_on_startup=False)
    with pytest.raises(RuntimeError, match="boom"):
        async with lifespan(FastAPI()):
            pass

    broker.shutdown.assert_awaited_once()
