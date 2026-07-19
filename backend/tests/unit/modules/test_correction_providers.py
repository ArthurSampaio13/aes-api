import pytest
from pydantic import ValidationError

from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate, CriterionScore
from src.modules.aes.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_valid_structured_candidate():
    provider = MockProvider()
    response = await provider.correct(essay_text="Um texto de teste.", prompt="Corrija: {essay_text}", params={})

    assert response.validation_error is None
    assert isinstance(response.structured, CorrectionCandidate)
    assert response.structured.sugestao_acionavel
    assert response.tokens_in > 0
    assert response.tokens_out > 0
    assert response.latency_ms >= 0


def test_criterion_score_rejects_out_of_range_nota():
    with pytest.raises(ValueError):
        CriterionScore(nota=99, justificativa="fora da escala")


def test_correction_candidate_rejects_missing_criterion():
    with pytest.raises(ValidationError):
        CorrectionCandidate.model_validate(
            {
                "scores": {
                    "adequacao_tema": {"nota": 5, "justificativa": "ok"},
                    "estrutura_textual": {"nota": 5, "justificativa": "ok"},
                },
                "feedback": "feedback qualquer",
                "sugestao_acionavel": "sugestão qualquer",
            }
        )


def test_correction_candidate_rejects_unknown_criterion_key():
    scores = {c: {"nota": 5, "justificativa": "ok"} for c in FIXED_CRITERIA}
    del scores["vocabulario"]
    scores["ortografia"] = {"nota": 5, "justificativa": "ok"}
    with pytest.raises(ValidationError):
        CorrectionCandidate.model_validate(
            {"scores": scores, "feedback": "feedback qualquer", "sugestao_acionavel": "sugestão qualquer"}
        )


def test_correction_candidate_requires_sugestao_acionavel():
    scores = {c: {"nota": 5, "justificativa": "ok"} for c in FIXED_CRITERIA}
    with pytest.raises(ValidationError):
        CorrectionCandidate.model_validate({"scores": scores, "feedback": "feedback qualquer"})


def test_correction_candidate_accepts_complete_payload():
    scores = {c: {"nota": 5, "justificativa": "ok"} for c in FIXED_CRITERIA}
    candidate = CorrectionCandidate.model_validate(
        {"scores": scores, "feedback": "feedback qualquer", "sugestao_acionavel": "sugestão qualquer"}
    )
    assert candidate.sugestao_acionavel == "sugestão qualquer"
