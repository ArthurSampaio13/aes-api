import httpx
import pytest

from src.modules.aes.providers.openrouter import OpenRouterProvider


@pytest.mark.asyncio
async def test_openrouter_provider_parses_usage_and_content(monkeypatch):
    async def fake_post(self, url, json, headers):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"scores": {}, "feedback": "ok"}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 60},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={"temperature": 0.0})

    assert response.tokens_in == 100
    assert response.tokens_out == 60
    assert response.raw_text == '{"scores": {}, "feedback": "ok"}'
