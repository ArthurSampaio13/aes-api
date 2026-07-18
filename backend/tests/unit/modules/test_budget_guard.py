import pytest

from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob
from src.modules.aes.models.essay_prompt import EssayPrompt
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.aes.models.submission import Batch, Submission
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.service import AesService
from src.modules.common.exceptions import BudgetExceededError
from src.modules.municipio.models import Municipio


@pytest.mark.asyncio
async def test_check_budget_raises_when_month_spend_exceeds_limit(db_session, test_user):
    municipio = Municipio(nome="Budget Test", monthly_token_budget=100)
    db_session.add(municipio)
    await db_session.commit()

    rubric = Rubric(
        version=1,
        criteria={c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA},
        municipio_id=municipio.id,
    )
    template = PromptTemplate(version=1, template_text="Corrija: {essay_text}", municipio_id=municipio.id)
    db_session.add_all([rubric, template])
    await db_session.flush()
    essay_prompt = EssayPrompt(
        municipio_id=municipio.id,
        titulo="Teste",
        enunciado="Escreva sobre...",
        ano_escolar="9",
        genero_textual="dissertativo-argumentativo",
        rubric_id=rubric.id,
        prompt_template_id=template.id,
    )
    db_session.add(essay_prompt)
    await db_session.flush()

    batch = Batch(municipio_id=municipio.id, essay_prompt_id=essay_prompt.uuid, created_by_user_id=test_user["id"])
    db_session.add(batch)
    await db_session.flush()
    submission = Submission(municipio_id=municipio.id, batch_id=batch.uuid, input_type="text", original_ref="", raw_text="x")
    db_session.add(submission)
    await db_session.flush()
    job = CorrectionJob(
        municipio_id=municipio.id, submission_id=submission.uuid, provider="mock", model="mock-v1", status="done"
    )
    db_session.add(job)
    await db_session.flush()
    attempt = CorrectionAttempt(
        municipio_id=municipio.id,
        correction_job_id=job.uuid,
        attempt_number=1,
        provider="mock",
        model="mock-v1",
        prompt_version=1,
        rubric_version=1,
        inference_params={},
        outcome="success",
        tokens_in=80,
        tokens_out=50,
    )
    db_session.add(attempt)
    await db_session.commit()

    service = AesService()
    with pytest.raises(BudgetExceededError):
        await service.check_budget(municipio.id, db_session)


@pytest.mark.asyncio
async def test_check_budget_passes_when_under_limit(db_session):
    municipio = Municipio(nome="Budget Test 2", monthly_token_budget=None)
    db_session.add(municipio)
    await db_session.commit()

    service = AesService()
    await service.check_budget(municipio.id, db_session)
