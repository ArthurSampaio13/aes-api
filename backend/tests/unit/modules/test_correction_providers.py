import pytest

from src.modules.aes.providers.base import CorrectionCandidate, CriterionScore
from src.modules.aes.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_valid_structured_candidate():
    provider = MockProvider()
    response = await provider.correct(essay_text="Um texto de teste.", prompt="Corrija: {essay_text}", params={})

    assert response.validation_error is None
    assert isinstance(response.structured, CorrectionCandidate)
    assert response.tokens_in > 0
    assert response.tokens_out > 0
    assert response.latency_ms >= 0


def test_criterion_score_rejects_out_of_range_nota():
    with pytest.raises(ValueError):
        CriterionScore(nota=99, justificativa="fora da escala")
