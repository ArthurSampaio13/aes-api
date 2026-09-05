from typing import Any

import pytest
from sqlalchemy import select

from src.infrastructure.config.settings import get_settings
from src.modules.aes.metrics import CORRECTION_JOBS_TOTAL
from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from src.modules.aes.models.submission import Submission
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.ocr_base import OCRResult
from src.modules.aes.storage import ObjectStorage
from tests.conftest import FakeS3Client


@pytest.mark.asyncio
async def test_worker_persists_attempt_and_result_on_success(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()

    jobs_done_before = CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1")._value.get()

    await correction_job_fixture.process(municipio, job)

    jobs_done_after = CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1")._value.get()
    assert jobs_done_after == jobs_done_before + 1

    db_session = correction_job_fixture.db_session
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


@pytest.mark.asyncio
async def test_worker_redelivery_of_done_job_is_a_no_op(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()

    for _ in range(2):
        await correction_job_fixture.process(municipio, job)

    db_session = correction_job_fixture.db_session
    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert len(attempts) == 1

    results_query = select(CorrectionResult).where(CorrectionResult.correction_job_id == job.uuid)
    results = (await db_session.execute(results_query)).scalars().all()
    assert len(results) == 1

    await db_session.refresh(job)
    assert job.status == "done"


class _RaisingProvider:
    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]):
        raise RuntimeError("provider exploded")


@pytest.mark.asyncio
async def test_worker_marks_job_failed_when_provider_raises(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    job_uuid = job.uuid

    with pytest.raises(RuntimeError, match="provider exploded"):
        await correction_job_fixture.process(municipio, job, provider=_RaisingProvider())

    db_session = correction_job_fixture.db_session
    refetched = (await db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_uuid))).scalar_one()
    assert refetched.status == "failed"


@pytest.mark.asyncio
async def test_worker_persists_raw_response_to_object_storage(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    fake_client = FakeS3Client()
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: fake_client)

    await correction_job_fixture.process(municipio, job, object_storage=storage)

    assert len(fake_client.put_calls) == 1
    assert fake_client.put_calls[0]["Bucket"] == "test-bucket"
    assert "raw_response.txt" in fake_client.put_calls[0]["Key"]

    db_session = correction_job_fixture.db_session
    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert len(attempts) == 1
    assert attempts[0].raw_response_ref is not None
    assert "raw_response.txt" in attempts[0].raw_response_ref


@pytest.mark.asyncio
async def test_worker_stamps_code_version_on_attempt(correction_job_fixture, monkeypatch):
    monkeypatch.setattr(get_settings(), "CODE_VERSION", "test-sha-abc123")

    municipio, job = await correction_job_fixture.build()

    await correction_job_fixture.process(municipio, job)

    db_session = correction_job_fixture.db_session
    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert attempts[0].code_version == "test-sha-abc123"


class _RecordingOCRProvider:
    def __init__(self):
        self.received_bytes: bytes | None = None

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        self.received_bytes = image_bytes
        return OCRResult(text="texto extraído da imagem")


@pytest.mark.asyncio
async def test_worker_fetches_image_bytes_from_storage_for_ocr(correction_job_fixture):
    municipio, job = await correction_job_fixture.build(
        input_type="image", raw_text=None, original_ref="submissions/x/original.jpg"
    )

    fake_client = _GettableFakeS3Client(objects={"submissions/x/original.jpg": b"fake-image-bytes"})
    ocr_provider = _RecordingOCRProvider()

    await correction_job_fixture.process(
        municipio,
        job,
        provider=MockProvider(),
        ocr_provider=ocr_provider,
        object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: fake_client),
    )

    assert ocr_provider.received_bytes == b"fake-image-bytes"
    db_session = correction_job_fixture.db_session
    submission = (await db_session.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalar_one()
    assert submission.raw_text == "texto extraído da imagem"


class _GettableFakeS3Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects

    async def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body

    async def get_object(self, Bucket, Key):
        class _Body:
            def __init__(self, data):
                self._data = data

            async def read(self):
                return self._data

        return {"Body": _Body(self.objects[Key])}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False
