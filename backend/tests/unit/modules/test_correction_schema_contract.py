"""O schema precisa exigir os cinco critérios, não só permiti-los.

Um `dict[CriterionName, CriterionScore]` vira `propertyNames.enum` no JSON
Schema: diz quais chaves são aceitas e nenhuma obrigatória. O modelo então
responde `"scores": {}`, que é válido pelo schema, e só o validador em Python
rejeita — tarde demais e sem sinal algum para o modelo.
"""

import pytest
from pydantic import ValidationError

from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate

VALID_SCORE = {"nota": 4, "justificativa": "ok"}


def test_schema_requires_every_criterion() -> None:
    scores = CorrectionCandidate.model_json_schema()["$defs"]["CriterionScores"]
    assert sorted(scores["required"]) == sorted(FIXED_CRITERIA), scores


def test_empty_scores_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CorrectionCandidate(scores={}, feedback="ok", sugestao_acionavel="ok")


def test_unknown_criterion_is_rejected() -> None:
    scores = {c: VALID_SCORE for c in FIXED_CRITERIA} | {"ortografia": VALID_SCORE}
    with pytest.raises(ValidationError):
        CorrectionCandidate(scores=scores, feedback="ok", sugestao_acionavel="ok")


def test_serialised_shape_is_unchanged() -> None:
    candidate = CorrectionCandidate(scores={c: VALID_SCORE for c in FIXED_CRITERIA}, feedback="ok", sugestao_acionavel="ok")
    assert sorted(candidate.model_dump()["scores"]) == sorted(FIXED_CRITERIA)
