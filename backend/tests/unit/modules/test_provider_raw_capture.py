"""O que foi enviado e o que voltou, verbatim, inclusive quando a corrida falha.

Sem isso não há como auditar uma correção nem reproduzi-la: a falha que mais importa é justamente a que não produz saída
estruturada, e era exatamente nela que o registro vinha vazio.
"""

import json

import pytest
from pydantic_ai.models.test import TestModel

from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.openrouter import OpenRouterProvider

VALID_SCORES = {c: {"nota": 7, "justificativa": "ok"} for c in FIXED_CRITERIA}


def _provider() -> OpenRouterProvider:
    return OpenRouterProvider(api_key="test-key", model="modelo/teste")


async def _run(output_args: dict) -> object:
    provider = _provider()
    with provider.agent.override(model=TestModel(custom_output_args=output_args)):
        return await provider.correct(
            essay_text="a redação do aluno", prompt="corrija isto: {essay_text}", params={"temperature": 0.0}
        )


@pytest.mark.asyncio
async def test_request_records_model_settings_and_output_schema() -> None:
    response = await _run({"scores": VALID_SCORES, "feedback": "ok", "sugestao_acionavel": "ok"})

    request = json.loads(response.raw_request)
    assert request["model"] == "modelo/teste"
    assert request["model_settings"]["temperature"] == 0.0
    assert "corrija isto:" in request["instructions"]
    assert request["user_content"] == "a redação do aluno"
    assert sorted(request["output_schema"]["$defs"]["CriterionScores"]["required"]) == sorted(FIXED_CRITERIA)


@pytest.mark.asyncio
async def test_response_is_recorded_verbatim() -> None:
    response = await _run({"scores": VALID_SCORES, "feedback": "ok", "sugestao_acionavel": "ok"})

    assert "sugestao_acionavel" in response.raw_response
    assert json.loads(response.raw_response)


@pytest.mark.asyncio
async def test_both_sides_survive_a_failed_run() -> None:
    response = await _run({"scores": {}, "feedback": "ok", "sugestao_acionavel": "ok"})

    assert response.structured is None
    assert response.validation_error is not None
    assert json.loads(response.raw_request)["model"] == "modelo/teste"
    assert response.raw_response, "a resposta recusada é o registro mais importante de todos"
