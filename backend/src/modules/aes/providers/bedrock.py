"""Amazon Bedrock provider — pydantic-ai Agent over the Bedrock Converse API."""

from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel

from ._pydantic_ai_support import run_agent
from .base import CorrectionCandidate, ProviderResponse


class BedrockProvider:
    def __init__(self, model_id: str) -> None:
        pydantic_model = BedrockConverseModel(model_id)
        self.agent = Agent(pydantic_model, output_type=CorrectionCandidate, output_retries=0)

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        return await run_agent(
            self.agent,
            essay_text=essay_text,
            prompt=prompt,
            model_settings={
                "temperature": params.get("temperature", 0.0),
                "bedrock_cache_instructions": True,
            },
        )
