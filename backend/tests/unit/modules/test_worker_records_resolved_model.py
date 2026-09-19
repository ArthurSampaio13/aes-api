"""A tentativa registra o modelo do job, não o model_id do provider.

`provider.model_id` é o id prefixado que a pydantic-ai resolve (`openrouter:<modelo>`); `job.model` é o id bare
gravado na submissão. Gravar o do provider faria `CorrectionAttempt.model` divergir de `CorrectionJob.model` para o
mesmo job.
"""

import pytest
from sqlalchemy import select

from src.modules.aes.models.correction import CorrectionAttempt
from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate, ProviderResponse

_CANDIDATE = CorrectionCandidate(
    scores={c: {"nota": 7, "justificativa": "ok"} for c in FIXED_CRITERIA},
    feedback="ok",
    sugestao_acionavel="ok",
)


class _FakeProvider:
    model_id = "openrouter:a-different-model"

    async def correct(self, essay_text: str, prompt: str, params: dict) -> ProviderResponse:
        return ProviderResponse(raw_text="ok", structured=_CANDIDATE, tokens_in=1, tokens_out=1, latency_ms=1)


@pytest.mark.asyncio
async def test_attempt_records_the_job_model_not_the_provider_model_id(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()

    await correction_job_fixture.process(municipio, job, provider=_FakeProvider())

    db_session = correction_job_fixture.db_session
    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempt = (await db_session.execute(attempts_query)).scalar_one()

    assert attempt.model == job.model == "mock-v1"
    assert attempt.model != _FakeProvider.model_id
