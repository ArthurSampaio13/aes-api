import pytest

from src.modules.aes.catalog import fetch_catalog

RESPOSTA = {
    "data": [
        {
            "id": "deepseek/deepseek-v4.1-flash",
            "architecture": {"input_modalities": ["text", "image"]},
            "pricing": {"prompt": "0.0000003", "completion": "0.0000025"},
        },
        {
            "id": "deepseek/deepseek-chat",
            "architecture": {"input_modalities": ["text"]},
            "pricing": {"prompt": "0.0000001", "completion": "0.0000002"},
        },
    ]
}


class _FakeResponse:
    def json(self):
        return RESPOSTA

    def raise_for_status(self):
        return None


class _FakeClient:
    async def get(self, url, **kwargs):
        return _FakeResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_catalog_is_keyed_by_model_id():
    catalogo = await fetch_catalog(client_factory=lambda: _FakeClient())
    assert set(catalogo) == {"deepseek/deepseek-v4.1-flash", "deepseek/deepseek-chat"}


@pytest.mark.asyncio
async def test_catalog_keeps_modalities_and_price():
    catalogo = await fetch_catalog(client_factory=lambda: _FakeClient())
    flash = catalogo["deepseek/deepseek-v4.1-flash"]
    assert flash.input_modalities == ["text", "image"]
    assert flash.prompt_price == pytest.approx(0.0000003)
