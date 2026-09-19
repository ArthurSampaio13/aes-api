"""Taskiq task: consumes a CorrectionJob, runs OCR (if needed) + LLM correction, persists the attempt history."""

from typing import Annotated, Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends, TaskiqEvents, TaskiqState

from ...infrastructure.config.settings import get_settings
from ...infrastructure.database.tenancy import set_tenant_context
from ...infrastructure.taskiq.brokers import default_broker
from ...infrastructure.taskiq.deps import get_db_session
from .metrics import (
    CORRECTION_ATTEMPTS_TOTAL,
    CORRECTION_CACHE_TOKENS,
    CORRECTION_JOBS_TOTAL,
    CORRECTION_LATENCY_MS,
    CORRECTION_TOKENS,
    GUARDRAIL_VERDICTS_TOTAL,
    start_metrics_server,
)
from .models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from .models.submission import Submission
from .providers._pydantic_ai_support import openrouter_model_settings
from .providers.base import CorrectionProvider
from .providers.ocr_base import OCRProvider
from .providers.registry import get_ocr_provider, get_provider
from .storage import ObjectStorage, get_object_storage

_TERMINAL_STATUSES = ("done", "failed")


async def _transcribe_if_needed(
    submission: Submission,
    ocr_provider: OCRProvider,
    object_storage: ObjectStorage,
    db: AsyncSession,
    municipio_id: int,
    job_logger: Any,
) -> str:
    if submission.raw_text:
        return submission.raw_text

    image_bytes = await object_storage.get(submission.original_ref)
    ocr_result = await ocr_provider.extract_text(image_bytes=image_bytes)

    meta = dict(ocr_result.meta)
    raw_exchange = meta.pop("raw_exchange", "")
    if raw_exchange:
        meta["raw_exchange_ref"] = await object_storage.put(
            key=f"transcriptions/{submission.uuid}/exchange.json",
            content=raw_exchange.encode("utf-8"),
            content_type="application/json",
        )

    submission.raw_text = ocr_result.text
    submission.transcription_meta = meta
    await db.commit()
    await set_tenant_context(db, municipio_id, is_superuser=False)
    job_logger.bind(model_retries=meta.get("model_retries"), palavras=meta.get("palavras")).info("ocr transcription completed")
    return ocr_result.text


async def _run_attempt(
    job: CorrectionJob,
    attempt_number: int,
    essay_text: str,
    prompt_text: str,
    prompt_version: int,
    rubric_version: int,
    provider: CorrectionProvider,
    object_storage: ObjectStorage,
    db: AsyncSession,
    job_logger: Any,
) -> CorrectionAttempt:
    inference_params = {"temperature": 0.0} if job.provider == "mock" else openrouter_model_settings(0.0)
    response = await provider.correct(essay_text=essay_text, prompt=prompt_text, params=inference_params)

    outcome = "success" if response.structured is not None else ("retry" if attempt_number < job.max_attempts else "failed")

    prefix = f"correction-attempts/{job.uuid}/attempt-{attempt_number}"

    async def _store(name: str, payload: str) -> str | None:
        if not payload:
            return None
        return await object_storage.put(
            key=f"{prefix}/{name}",
            content=payload.encode("utf-8"),
            content_type="application/json",
        )

    raw_request_ref = await _store("request.json", response.raw_request)
    raw_response_ref = await _store("response.json", response.raw_response)

    attempt = CorrectionAttempt(
        municipio_id=job.municipio_id,
        correction_job_id=job.uuid,
        attempt_number=attempt_number,
        provider=job.provider,
        model=job.model,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
        inference_params=inference_params,
        outcome=outcome,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        latency_ms=response.latency_ms,
        raw_request_ref=raw_request_ref,
        raw_response_ref=raw_response_ref,
        code_version=get_settings().CODE_VERSION,
        validation_errors={"error": response.validation_error} if response.validation_error else None,
        error_message=response.validation_error,
        cache_read_tokens=response.cache_read_tokens,
        cache_write_tokens=response.cache_write_tokens,
        cost_usd=response.cost_usd,
        served_provider=response.served_provider,
        guardrail_events=response.guardrail_events or None,
        model_retries=response.model_retries,
    )
    db.add(attempt)
    await db.flush()

    job_logger.bind(
        attempt_number=attempt_number,
        outcome=outcome,
        latency_ms=response.latency_ms,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        validation_error_type=response.validation_error_type,
    ).info("correction attempt finished")

    CORRECTION_TOKENS.labels(provider=job.provider, model=job.model, direction="in").observe(response.tokens_in)
    CORRECTION_TOKENS.labels(provider=job.provider, model=job.model, direction="out").observe(response.tokens_out)
    CORRECTION_LATENCY_MS.labels(provider=job.provider, model=job.model).observe(response.latency_ms)
    CORRECTION_ATTEMPTS_TOTAL.labels(provider=job.provider, model=job.model, outcome=outcome).inc()
    CORRECTION_CACHE_TOKENS.labels(provider=job.provider, model=job.model, direction="read").observe(response.cache_read_tokens)
    CORRECTION_CACHE_TOKENS.labels(provider=job.provider, model=job.model, direction="write").observe(
        response.cache_write_tokens
    )
    for evento in response.guardrail_events:
        GUARDRAIL_VERDICTS_TOTAL.labels(guard=evento["guard"], veredito=evento["veredito"]).inc()

    if response.structured is not None:
        result = CorrectionResult(
            municipio_id=job.municipio_id,
            correction_job_id=job.uuid,
            correction_attempt_id=attempt.uuid,
            scores=response.structured.scores.model_dump(),
            feedback=response.structured.feedback,
            sugestao_acionavel=response.structured.sugestao_acionavel,
        )
        insert_result = (
            pg_insert(CorrectionResult)
            .values(
                uuid=result.uuid,
                municipio_id=result.municipio_id,
                correction_job_id=result.correction_job_id,
                correction_attempt_id=result.correction_attempt_id,
                scores=result.scores,
                feedback=result.feedback,
                sugestao_acionavel=result.sugestao_acionavel,
                requires_teacher_review=result.requires_teacher_review,
                created_at=result.created_at,
                updated_at=result.updated_at,
            )
            .on_conflict_do_nothing(index_elements=["correction_job_id"])
        )
        await db.execute(insert_result)
        job.status = "done"
        CORRECTION_JOBS_TOTAL.labels(status=job.status, provider=job.provider, model=job.model).inc()
        await db.commit()
        job_logger.info("correction job done")

    return attempt


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
            essay_text = await _transcribe_if_needed(submission, ocr_provider, object_storage, db, municipio_id, job_logger)
        assert essay_text is not None

        for attempt_number in range(1, job.max_attempts + 1):
            attempt = await _run_attempt(
                job,
                attempt_number,
                essay_text,
                prompt_text,
                prompt_version,
                rubric_version,
                provider,
                object_storage,
                db,
                job_logger,
            )
            if attempt.outcome == "success":
                return

        job.status = "failed"
        CORRECTION_JOBS_TOTAL.labels(status=job.status, provider=job.provider, model=job.model).inc()
        await db.commit()
        job_logger.warning("correction job failed after exhausting attempts")
    except Exception:
        await db.rollback()
        await set_tenant_context(db, municipio_id, is_superuser=False)
        job = (await db.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_id))).scalar_one()
        if job.status != "done":
            job.status = "failed"
        await db.commit()
        job_logger.exception("correction job failed with an unhandled error")
        raise


@default_broker.task(task_name="run_correction_job")
async def run_correction_job(
    job_id: str,
    municipio_id: int,
    provider_name: str,
    model_name: str | None,
    prompt_text: str,
    prompt_version: int,
    rubric_version: int,
    db: Annotated[AsyncSession, TaskiqDepends(get_db_session)],
) -> None:
    await process_correction_job(
        job_id=job_id,
        municipio_id=municipio_id,
        db=db,
        provider=get_provider(provider_name, model_name),
        ocr_provider=get_ocr_provider(get_settings().AES_OCR_PROVIDER),
        object_storage=get_object_storage(),
        prompt_text=prompt_text,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
    )


@default_broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _serve_worker_metrics(_: TaskiqState) -> None:
    start_metrics_server(get_settings().WORKER_METRICS_PORT)
