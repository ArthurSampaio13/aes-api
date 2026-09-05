"""Taskiq task: consumes a CorrectionJob, runs OCR (if needed) + LLM correction, persists the attempt history."""

import time
from typing import Annotated

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends, TaskiqEvents, TaskiqState

from ...infrastructure.config.settings import get_settings
from ...infrastructure.database.tenancy import set_tenant_context
from ...infrastructure.taskiq.brokers import default_broker
from ...infrastructure.taskiq.deps import get_db_session
from .metrics import (
    CORRECTION_ATTEMPTS_TOTAL,
    CORRECTION_JOBS_TOTAL,
    CORRECTION_LATENCY_MS,
    CORRECTION_TOKENS,
    start_metrics_server,
)
from .models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from .models.submission import Submission
from .providers.base import CorrectionProvider
from .providers.ocr_base import OCRProvider
from .providers.registry import get_ocr_provider, get_provider
from .storage import ObjectStorage, get_object_storage

_TERMINAL_STATUSES = ("done", "failed")


async def process_correction_job(
    job_id: str,
    municipio_id: int,
    db: AsyncSession,
    provider: CorrectionProvider,
    ocr_provider: OCRProvider,
    object_storage: ObjectStorage,
    prompt_text: str,
    prompt_version: int,
    rubric_version: int,
) -> None:
    await set_tenant_context(db, municipio_id, is_superuser=False)
    job = (await db.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_id))).scalar_one()
    if job.status in _TERMINAL_STATUSES:
        return
    submission = (await db.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalar_one()

    job_logger = logger.bind(
        job_id=str(job.uuid),
        submission_id=str(submission.uuid),
        municipio_id=municipio_id,
        provider=job.provider,
        model=job.model,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
    )
    job_logger.info("correction job started")

    job.status = "processing"
    await db.commit()
    await set_tenant_context(db, municipio_id, is_superuser=False)

    try:
        essay_text = submission.raw_text
        if submission.input_type == "image" and not essay_text:
            image_bytes = await object_storage.get(submission.original_ref)
            ocr_result = await ocr_provider.extract_text(image_bytes=image_bytes)
            essay_text = ocr_result.text
            submission.raw_text = essay_text
            await db.commit()
            await set_tenant_context(db, municipio_id, is_superuser=False)
            job_logger.info("ocr transcription completed")
        assert essay_text is not None

        for attempt_number in range(1, job.max_attempts + 1):
            started_at = time.monotonic()
            response = await provider.correct(essay_text=essay_text, prompt=prompt_text, params={"temperature": 0.0})
            latency_ms = int((time.monotonic() - started_at) * 1000)

            outcome = (
                "success" if response.structured is not None else ("retry" if attempt_number < job.max_attempts else "failed")
            )

            raw_response_ref: str | None = None
            if response.raw_text:
                raw_response_ref = await object_storage.put(
                    key=f"correction-attempts/{job.uuid}/attempt-{attempt_number}/raw_response.txt",
                    content=response.raw_text.encode("utf-8"),
                    content_type="text/plain",
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
                raw_response_ref=raw_response_ref,
                code_version=get_settings().CODE_VERSION,
                validation_errors={"error": response.validation_error} if response.validation_error else None,
                error_message=response.validation_error,
            )
            db.add(attempt)
            await db.flush()

            job_logger.bind(
                attempt_number=attempt_number,
                outcome=outcome,
                latency_ms=latency_ms,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                validation_error=response.validation_error,
            ).info("correction attempt finished")

            CORRECTION_TOKENS.labels(provider=job.provider, model=job.model, direction="in").observe(response.tokens_in)
            CORRECTION_TOKENS.labels(provider=job.provider, model=job.model, direction="out").observe(response.tokens_out)
            CORRECTION_LATENCY_MS.labels(provider=job.provider, model=job.model).observe(latency_ms)
            CORRECTION_ATTEMPTS_TOTAL.labels(provider=job.provider, model=job.model, outcome=outcome).inc()

            if response.structured is not None:
                result = CorrectionResult(
                    municipio_id=job.municipio_id,
                    correction_job_id=job.uuid,
                    correction_attempt_id=attempt.uuid,
                    scores={k: v.model_dump() for k, v in response.structured.scores.items()},
                    feedback=response.structured.feedback,
                    sugestao_acionavel=response.structured.sugestao_acionavel,
                )
                db.add(result)
                job.status = "done"
                CORRECTION_JOBS_TOTAL.labels(status=job.status, provider=job.provider, model=job.model).inc()
                await db.commit()
                job_logger.info("correction job done")
                return

        job.status = "failed"
        CORRECTION_JOBS_TOTAL.labels(status=job.status, provider=job.provider, model=job.model).inc()
        await db.commit()
        job_logger.warning("correction job failed after exhausting attempts")
    except Exception:
        await db.rollback()
        await set_tenant_context(db, municipio_id, is_superuser=False)
        job = (await db.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_id))).scalar_one()
        job.status = "failed"
        await db.commit()
        job_logger.exception("correction job failed with an unhandled error")
        raise


@default_broker.task(task_name="run_correction_job")
async def run_correction_job(
    job_id: str,
    municipio_id: int,
    provider_name: str,
    prompt_text: str,
    prompt_version: int,
    rubric_version: int,
    db: Annotated[AsyncSession, TaskiqDepends(get_db_session)],
) -> None:
    await process_correction_job(
        job_id=job_id,
        municipio_id=municipio_id,
        db=db,
        provider=get_provider(provider_name),
        ocr_provider=get_ocr_provider(get_settings().AES_OCR_PROVIDER),
        object_storage=get_object_storage(),
        prompt_text=prompt_text,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
    )


@default_broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _serve_worker_metrics(_: TaskiqState) -> None:
    start_metrics_server(get_settings().WORKER_METRICS_PORT)
