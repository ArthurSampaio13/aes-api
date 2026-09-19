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
async def test_catalog_outage_does_not_block_submission():
    """Indisponibilidade de terceiro não pode derrubar a submissão."""
    await AesService().ensure_model_is_known("openrouter", "qualquer/coisa", _catalogo_indisponivel)
