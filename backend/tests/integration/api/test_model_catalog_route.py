import pytest

from src.modules.aes import routes
from src.modules.aes.catalog import ModelInfo


@pytest.mark.asyncio
async def test_models_route_filters_by_modality(auth_client, monkeypatch):
    async def fake_catalog(*args, **kwargs):
        return {
            "a": ModelInfo(id="a", input_modalities=["text"], prompt_price=0.0, completion_price=0.0),
            "b": ModelInfo(id="b", input_modalities=["text", "image"], prompt_price=0.0, completion_price=0.0),
        }

    monkeypatch.setattr(routes, "fetch_catalog", fake_catalog)

    response = await auth_client.get("/api/v1/aes/models?input_modality=image")

    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["b"]


@pytest.mark.asyncio
async def test_models_route_returns_empty_list_when_catalog_fetch_fails(auth_client, monkeypatch):
    async def failing_catalog(*args, **kwargs):
        raise RuntimeError("openrouter is down")

    monkeypatch.setattr(routes, "fetch_catalog", failing_catalog)

    response = await auth_client.get("/api/v1/aes/models")

    assert response.status_code == 200
    assert response.json() == []
