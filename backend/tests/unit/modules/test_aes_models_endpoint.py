import pytest

from src.infrastructure.config.settings import get_settings
from src.interfaces.main import app
from src.modules.aes.providers.openai_compatible import GATEWAY_BASE_URLS
from src.modules.aes.providers.registry import PROVIDER_FACTORIES
from src.modules.aes.routes import list_models


def test_models_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/aes/models" in paths


@pytest.mark.asyncio
async def test_lists_every_registered_provider():
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})

    assert {entry["provider"] for entry in payload} == set(PROVIDER_FACTORIES)


@pytest.mark.asyncio
async def test_mock_provider_is_always_available():
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})

    mock_entry = next(entry for entry in payload if entry["provider"] == "mock")
    assert mock_entry["available"] is True
    assert mock_entry["model"] == "mock"


@pytest.mark.asyncio
async def test_openrouter_availability_follows_credentials(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None, raising=False)
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})

    entry = next(item for item in payload if item["provider"] == "openrouter")
    assert entry["available"] is False


@pytest.mark.asyncio
async def test_lists_every_gateway_preset():
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})
    listed = {entry["provider"] for entry in payload}

    for name in GATEWAY_BASE_URLS:
        assert name in listed, name


@pytest.mark.asyncio
async def test_gateway_availability_follows_credentials(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "GROQ_API_KEY", None, raising=False)
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})
    assert next(e for e in payload if e["provider"] == "groq")["available"] is False

    monkeypatch.setattr(settings, "GROQ_API_KEY", "a-key", raising=False)
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})
    assert next(e for e in payload if e["provider"] == "groq")["available"] is True
