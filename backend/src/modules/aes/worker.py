"""Taskiq task: consumes a CorrectionJob, runs OCR (if needed) + LLM correction, persists the attempt history."""

import time
from typing import Annotated

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from ...infrastructure.database.tenancy import set_tenant_context
from ...infrastructure.taskiq.brokers import default_broker
from ...infrastructure.taskiq.deps import get_db_session
from .metrics import CORRECTION_JOBS_TOTAL, CORRECTION_LATENCY_MS, CORRECTION_TOKENS
from .models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from .models.submission import Submission
from .providers.base import CorrectionProvider
from .providers.mock import MockProvider
from .providers.mock_ocr import MockOCRProvider
from .providers.ocr_base import OCRProvider

_TERMINAL_STATUSES = ("done", "failed")


async def process_correction_job(
    job_id: str,
    municipio_id: int,
    db: AsyncSession,
    provider: CorrectionProvider,
    ocr_provider: OCRProvider,
    prompt_text: str,
    prompt_version: int,
    rubric_version: int,
) -> None:
    await set_tenant_context(db, municipio_id, is_superuser=False)
    job = (await db.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_id))).scalar_one()
    if job.status in _TERMINAL_STATUSES:
        return
    submission = (await db.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalar_one()

    job.status = "processing"
    await db.commit()

    try:
        essay_text = submission.raw_text
        if submission.input_type == "image" and not essay_text:
            ocr_result = await ocr_provider.extract_text(image_bytes=b"")
            essay_text = ocr_result.text
            submission.raw_text = essay_text
            await db.commit()
        assert essay_text is not None

        for attempt_number in range(1, job.max_attempts + 1):
            started_at = time.monotonic()
            response = await provider.correct(essay_text=essay_text, prompt=prompt_text, params={"temperature": 0.0})
            latency_ms = int((time.monotonic() - started_at) * 1000)

            outcome = (
                "success" if response.structured is not None else ("retry" if attempt_number < job.max_attempts else "failed")
            )

            attempt = CorrectionAttempt(
                municipio_id=job.municipio_id,
                correction_job_id=job.uuid,
                attempt_number=attempt_number,
                provider=job.provider,
                model=job.model,
                prompt_version=prompt_version,
                rubric_version=rubric_version,
                inference_params={"temperature": 0.0},
                outcome=outcome,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                latency_ms=latency_ms,
                validation_errors={"error": response.validation_error} if response.validation_error else None,
                error_message=response.validation_error,
            )
            db.add(attempt)
            await db.flush()

            CORRECTION_TOKENS.labels(provider=job.provider, model=job.model, direction="in").observe(response.tokens_in)
            CORRECTION_TOKENS.labels(provider=job.provider, model=job.model, direction="out").observe(response.tokens_out)
            CORRECTION_LATENCY_MS.labels(provider=job.provider, model=job.model).observe(latency_ms)

            if response.structured is not None:
                result = CorrectionResult(
                    municipio_id=job.municipio_id,
                    correction_job_id=job.uuid,
                    correction_attempt_id=attempt.uuid,
                    scores={k: v.model_dump() for k, v in response.structured.scores.items()},
                    feedback=response.structured.feedback,
                )
                db.add(result)
                job.status = "done"
                CORRECTION_JOBS_TOTAL.labels(status=job.status, provider=job.provider, model=job.model).inc()
                await db.commit()
                return

        job.status = "failed"
        CORRECTION_JOBS_TOTAL.labels(status=job.status, provider=job.provider, model=job.model).inc()
        await db.commit()
    except Exception:
        await db.rollback()
        job = (await db.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_id))).scalar_one()
        job.status = "failed"
        await db.commit()
        raise


@default_broker.task(task_name="run_correction_job")
async def run_correction_job(
    job_id: str,
    municipio_id: int,
    prompt_text: str,
    prompt_version: int,
    rubric_version: int,
    db: Annotated[AsyncSession, TaskiqDepends(get_db_session)],
) -> None:
    await process_correction_job(
        job_id=job_id,
        municipio_id=municipio_id,
        db=db,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        prompt_text=prompt_text,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
    )
