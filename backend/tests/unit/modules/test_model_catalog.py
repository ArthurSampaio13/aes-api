import pytest

from src.modules.aes.catalog import _reset_cache, fetch_catalog

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


@pytest.fixture(autouse=True)
def _clean_catalog_cache():
    _reset_cache()
    yield
    _reset_cache()


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


class _CountingClient:
    def __init__(self, counter: dict[str, int]):
        self._counter = counter

    async def get(self, url, **kwargs):
        self._counter["calls"] += 1
        return _FakeResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FailingClient:
    async def get(self, url, **kwargs):
        raise RuntimeError("openrouter is down")

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


@pytest.mark.asyncio
async def test_second_call_within_ttl_does_not_refetch():
    counter = {"calls": 0}

    def factory():
        return _CountingClient(counter)

    await fetch_catalog(client_factory=factory)
    await fetch_catalog(client_factory=factory)

    assert counter["calls"] == 1


@pytest.mark.asyncio
async def test_failed_fetch_does_not_poison_cache():
    with pytest.raises(RuntimeError):
        await fetch_catalog(client_factory=lambda: _FailingClient())

    counter = {"calls": 0}
    catalogo = await fetch_catalog(client_factory=lambda: _CountingClient(counter))

    assert counter["calls"] == 1
    assert set(catalogo) == {"deepseek/deepseek-v4.1-flash", "deepseek/deepseek-chat"}
