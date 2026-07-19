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


@pytest.mark.asyncio
async def test_openrouter_provider_returns_validation_error_on_http_failure(monkeypatch):
    async def fake_post(self, url, json, headers):
        return httpx.Response(429, json={"error": "rate limited"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_openrouter_provider_returns_validation_error_on_malformed_body(monkeypatch):
    async def fake_post(self, url, json, headers):
        return httpx.Response(200, content=b"not json", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_openrouter_provider_returns_validation_error_on_non_dict_usage(monkeypatch):
    async def fake_post(self, url, json, headers):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}], "usage": "not-a-dict"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_openrouter_provider_handles_literal_braces_in_prompt_template(monkeypatch):
    captured = {}

    async def fake_post(self, url, json, headers):
        captured["content"] = json["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}], "usage": {}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="mock-model")
    prompt_with_json_example = 'Responda como {"scores": {}, "feedback": "..."}. Redação: {essay_text}'
    await provider.correct(essay_text="texto do aluno", prompt=prompt_with_json_example, params={})

    assert captured["content"] == 'Responda como {"scores": {}, "feedback": "..."}. Redação: texto do aluno'
