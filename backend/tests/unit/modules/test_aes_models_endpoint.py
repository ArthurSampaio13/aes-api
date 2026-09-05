import pytest

from src.infrastructure.config.settings import get_settings
from src.interfaces.main import app
from src.modules.aes.routes import list_models


def test_models_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/aes/models" in paths


@pytest.mark.asyncio
async def test_lists_every_registered_provider():
    payload = await list_models(current_user={"id": 1, "municipio_id": 7})

    assert {entry["provider"] for entry in payload} == {"mock", "openrouter", "bedrock"}


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
