from unittest.mock import AsyncMock, patch

import pytest

from src.modules.aes.routes import get_essay_prompt, get_rubric


@pytest.mark.asyncio
async def test_get_rubric_is_decorated_with_cache():
    assert hasattr(get_rubric, "__wrapped__")


@pytest.mark.asyncio
async def test_get_essay_prompt_is_decorated_with_cache():
    assert hasattr(get_essay_prompt, "__wrapped__")


@pytest.mark.asyncio
async def test_get_rubric_second_call_does_not_hit_service():
    from fastapi import Request

    request = Request(scope={"type": "http", "method": "GET", "headers": []})
    aes_service = AsyncMock()
    aes_service.get_rubric.return_value = {"id": 1, "version": 1, "criteria": {}, "municipio_id": None}

    with patch("src.infrastructure.cache.decorator.cache_provider") as mock_provider:
        backend = AsyncMock()
        backend.get.side_effect = [None, {"id": 1, "version": 1, "criteria": {}, "municipio_id": None}]
        mock_provider.get_backend.return_value = backend

        await get_rubric(rubric_id=1, municipio_id=7, db=AsyncMock(), aes_service=aes_service, request=request)
        await get_rubric(rubric_id=1, municipio_id=7, db=AsyncMock(), aes_service=aes_service, request=request)

    assert aes_service.get_rubric.call_count == 1
    assert backend.set.call_count == 1


@pytest.mark.asyncio
async def test_get_rubric_cache_key_is_scoped_by_municipio():
    from fastapi import Request

    request = Request(scope={"type": "http", "method": "GET", "headers": []})
    aes_service = AsyncMock()
    aes_service.get_rubric.return_value = {"id": 1, "version": 1, "criteria": {}, "municipio_id": 7}

    with patch("src.infrastructure.cache.decorator.cache_provider") as mock_provider:
        backend = AsyncMock()
        backend.get.return_value = None
        mock_provider.get_backend.return_value = backend

        await get_rubric(rubric_id=1, municipio_id=7, db=AsyncMock(), aes_service=aes_service, request=request)

    cache_key_used = backend.set.call_args.args[0]
    assert cache_key_used == "aes_rubric:7:1"
