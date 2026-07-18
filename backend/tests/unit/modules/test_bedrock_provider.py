import pytest

from src.modules.aes.providers.bedrock import BedrockProvider


class FakeBedrockClient:
    async def converse(self, modelId, messages, inferenceConfig):
        return {
            "output": {"message": {"content": [{"text": '{"scores": {}, "feedback": "ok"}'}]}},
            "usage": {"inputTokens": 90, "outputTokens": 45},
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_bedrock_provider_parses_usage_and_content():
    provider = BedrockProvider(model_id="anthropic.claude-3-haiku", client_factory=lambda: FakeBedrockClient())
    response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={"temperature": 0.0})

    assert response.tokens_in == 90
    assert response.tokens_out == 45
    assert response.raw_text == '{"scores": {}, "feedback": "ok"}'
