import pytest

from src.modules.aes.catalog import ModelInfo
from src.modules.aes.service import AesService
from src.modules.common.exceptions import ValidationError


async def _catalogo():
    return {
        "deepseek/deepseek-v4.1-flash": ModelInfo(
            id="deepseek/deepseek-v4.1-flash",
            input_modalities=["text", "image"],
            prompt_price=0.0,
            completion_price=0.0,
        )
    }


async def _catalogo_indisponivel():
    raise RuntimeError("openrouter fora do ar")


class _CountingLoader:
    """Conta chamadas para provar que o catálogo não foi consultado, não só que a chamada não quebrou."""

    def __init__(self):
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        return await _catalogo()


@pytest.mark.asyncio
async def test_known_model_passes():
    await AesService().ensure_model_is_known("openrouter", "deepseek/deepseek-v4.1-flash", _catalogo)


@pytest.mark.asyncio
async def test_unknown_model_is_rejected():
    with pytest.raises(ValidationError):
        await AesService().ensure_model_is_known("openrouter", "deepsek/typo", _catalogo)


@pytest.mark.asyncio
async def test_mock_never_touches_the_catalog():
    await AesService().ensure_model_is_known("mock", None, _catalogo_indisponivel)


@pytest.mark.asyncio
async def test_mock_with_unlisted_model_still_never_touches_the_catalog():
    """Pina o lado `provider == "mock"` do guard isoladamente: model é setado e não está no catálogo, então só o
    `not model` não explicaria a submissão passar sem rejeição."""
    loader = _CountingLoader()
    await AesService().ensure_model_is_known("mock", "deepsek/typo", loader)
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_openrouter_with_no_model_skips_validation_without_consulting_catalog():
    """Model=None cai no default configurado, não é um typo do chamador para pegar."""
    loader = _CountingLoader()
    await AesService().ensure_model_is_known("openrouter", None, loader)
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_catalog_outage_does_not_block_submission():
    """Indisponibilidade de terceiro não pode derrubar a submissão."""
    await AesService().ensure_model_is_known("openrouter", "qualquer/coisa", _catalogo_indisponivel)
