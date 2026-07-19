from typing import Any

import pytest
from sqlalchemy import select

from src.infrastructure.config.settings import get_settings
from src.modules.aes.metrics import CORRECTION_JOBS_TOTAL
from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from src.modules.aes.models.essay_prompt import EssayPrompt
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.aes.models.submission import Batch, Submission
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
from src.modules.aes.providers.ocr_base import OCRResult
from src.modules.aes.storage import ObjectStorage
from src.modules.aes.worker import process_correction_job
from src.modules.municipio.models import Municipio


class _FakeS3Client:
    def __init__(self):
        self.put_calls: list[dict] = []

    async def put_object(self, Bucket, Key, Body, ContentType):
        self.put_calls.append({"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def _build_pending_job(db_session, test_user, nome: str) -> tuple[Municipio, CorrectionJob]:
    municipio = Municipio(nome=nome)
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
    return municipio, job


@pytest.mark.asyncio
async def test_worker_persists_attempt_and_result_on_success(db_session, test_user):
    municipio, job = await _build_pending_job(db_session, test_user, "Worker Test")

    jobs_done_before = CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1")._value.get()

    await process_correction_job(
        job_id=str(job.uuid),
        municipio_id=municipio.id,
        db=db_session,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client()),
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    jobs_done_after = CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1")._value.get()
    assert jobs_done_after == jobs_done_before + 1

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
async def test_worker_redelivery_of_done_job_is_a_no_op(db_session, test_user):
    municipio, job = await _build_pending_job(db_session, test_user, "Redelivery Test")

    for _ in range(2):
        await process_correction_job(
            job_id=str(job.uuid),
            municipio_id=municipio.id,
            db=db_session,
            provider=MockProvider(),
            ocr_provider=MockOCRProvider(),
            object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client()),
            prompt_text="Corrija: {essay_text}",
            prompt_version=1,
            rubric_version=1,
        )

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
async def test_worker_marks_job_failed_when_provider_raises(db_session, test_user):
    municipio, job = await _build_pending_job(db_session, test_user, "Failure Boundary Test")
    job_uuid = job.uuid

    with pytest.raises(RuntimeError, match="provider exploded"):
        await process_correction_job(
            job_id=str(job_uuid),
            municipio_id=municipio.id,
            db=db_session,
            provider=_RaisingProvider(),
            ocr_provider=MockOCRProvider(),
            object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client()),
            prompt_text="Corrija: {essay_text}",
            prompt_version=1,
            rubric_version=1,
        )

    refetched = (await db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_uuid))).scalar_one()
    assert refetched.status == "failed"


@pytest.mark.asyncio
async def test_worker_persists_raw_response_to_object_storage(db_session, test_user):
    municipio, job = await _build_pending_job(db_session, test_user, "Raw Response Storage Test")
    fake_client = _FakeS3Client()
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: fake_client)

    await process_correction_job(
        job_id=str(job.uuid),
        municipio_id=municipio.id,
        db=db_session,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        object_storage=storage,
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    assert len(fake_client.put_calls) == 1
    assert fake_client.put_calls[0]["Bucket"] == "test-bucket"
    assert "raw_response.txt" in fake_client.put_calls[0]["Key"]

    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert len(attempts) == 1
    assert attempts[0].raw_response_ref is not None
    assert "raw_response.txt" in attempts[0].raw_response_ref


@pytest.mark.asyncio
async def test_worker_stamps_code_version_on_attempt(db_session, test_user, monkeypatch):
    monkeypatch.setattr(get_settings(), "CODE_VERSION", "test-sha-abc123")

    municipio, job = await _build_pending_job(db_session, test_user, "Code Version Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    await process_correction_job(
        job_id=str(job.uuid),
        municipio_id=municipio.id,
        db=db_session,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        object_storage=storage,
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert attempts[0].code_version == "test-sha-abc123"


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


class _RecordingOCRProvider:
    def __init__(self):
        self.received_bytes: bytes | None = None

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        self.received_bytes = image_bytes
        return OCRResult(text="texto extraído da imagem")


@pytest.mark.asyncio
async def test_worker_fetches_image_bytes_from_storage_for_ocr(db_session, test_user):
    municipio = Municipio(nome="OCR Wiring Test")
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
        municipio_id=municipio.id,
        batch_id=batch.uuid,
        input_type="image",
        original_ref="submissions/x/original.jpg",
        raw_text=None,
    )
    db_session.add(submission)
    await db_session.flush()
    job = CorrectionJob(
        municipio_id=municipio.id, submission_id=submission.uuid, provider="mock", model="mock-v1", status="pending"
    )
    db_session.add(job)
    await db_session.commit()

    fake_client = _GettableFakeS3Client(objects={"submissions/x/original.jpg": b"fake-image-bytes"})
    ocr_provider = _RecordingOCRProvider()

    await process_correction_job(
        job_id=str(job.uuid),
        municipio_id=municipio.id,
        db=db_session,
        provider=MockProvider(),
        ocr_provider=ocr_provider,
        object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: fake_client),
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    assert ocr_provider.received_bytes == b"fake-image-bytes"
    await db_session.refresh(submission)
    assert submission.raw_text == "texto extraído da imagem"
