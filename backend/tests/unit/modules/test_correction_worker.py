import pytest
from sqlalchemy import select

from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from src.modules.aes.models.essay_prompt import EssayPrompt
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.aes.models.submission import Batch, Submission
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
from src.modules.aes.worker import process_correction_job
from src.modules.municipio.models import Municipio


@pytest.mark.asyncio
async def test_worker_persists_attempt_and_result_on_success(db_session, test_user):
    municipio = Municipio(nome="Worker Test")
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
    submission = Submission(
        municipio_id=municipio.id, batch_id=batch.uuid, input_type="text", original_ref="", raw_text="Um texto de teste."
    )
    db_session.add(submission)
    await db_session.flush()
    job = CorrectionJob(
        municipio_id=municipio.id, submission_id=submission.uuid, provider="mock", model="mock-v1", status="pending"
    )
    db_session.add(job)
    await db_session.commit()

    await process_correction_job(
        job_id=str(job.uuid),
        db=db_session,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert len(attempts) == 1
    assert attempts[0].outcome == "success"
    assert attempts[0].tokens_in > 0

    results_query = select(CorrectionResult).where(CorrectionResult.correction_job_id == job.uuid)
    results = (await db_session.execute(results_query)).scalars().all()
    assert len(results) == 1
    assert results[0].requires_teacher_review is True

    await db_session.refresh(job)
    assert job.status == "done"
