from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select

from src.infrastructure.config.settings import get_settings
from src.modules.aes.metrics import CORRECTION_JOBS_TOTAL
from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from src.modules.aes.models.submission import Submission
from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate, ProviderResponse
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.ocr_base import OCRResult
from src.modules.aes.storage import ObjectStorage
from src.modules.common.exceptions import TranscriptionQualityError
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


@pytest.mark.asyncio
async def test_worker_converges_to_done_when_result_already_committed_by_another_delivery(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    db_session = correction_job_fixture.db_session

    other_delivery_attempt = CorrectionAttempt(
        municipio_id=municipio.id,
        correction_job_id=job.uuid,
        attempt_number=1,
        provider="mock",
        model="mock-v1",
        prompt_version=1,
        rubric_version=1,
        outcome="success",
    )
    db_session.add(other_delivery_attempt)
    await db_session.flush()
    db_session.add(
        CorrectionResult(
            municipio_id=municipio.id,
            correction_job_id=job.uuid,
            correction_attempt_id=other_delivery_attempt.uuid,
            scores={},
            feedback="corrigido por outra entrega da fila",
            sugestao_acionavel="",
        )
    )
    await db_session.commit()

    await correction_job_fixture.process(municipio, job)

    results_query = select(CorrectionResult).where(CorrectionResult.correction_job_id == job.uuid)
    results = (await db_session.execute(results_query)).scalars().all()
    assert len(results) == 1

    await db_session.refresh(job)
    assert job.status == "done"


class _RaisingProvider:
    model_id = "dublê"

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


class _RaisesAfterAnotherDeliveryAlreadyFinished:
    model_id = "dublê"

    def __init__(self, db_session, job_uuid: str):
        self.db_session = db_session
        self.job_uuid = job_uuid

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]):
        concurrent_job = (
            await self.db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid == self.job_uuid))
        ).scalar_one()
        concurrent_job.status = "done"
        await self.db_session.commit()
        raise RuntimeError("provider exploded after another delivery already finished")


@pytest.mark.asyncio
async def test_worker_does_not_downgrade_a_job_another_delivery_already_finished(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    job_uuid = job.uuid
    db_session = correction_job_fixture.db_session

    with pytest.raises(RuntimeError, match="provider exploded"):
        await correction_job_fixture.process(
            municipio, job, provider=_RaisesAfterAnotherDeliveryAlreadyFinished(db_session, str(job_uuid))
        )

    refetched = (await db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid == job_uuid))).scalar_one()
    assert refetched.status == "done"


@pytest.mark.asyncio
async def test_worker_persists_both_sides_of_the_exchange(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    fake_client = FakeS3Client()
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: fake_client)

    await correction_job_fixture.process(municipio, job, object_storage=storage)

    stored = {call["Key"].rsplit("/", 1)[-1] for call in fake_client.put_calls}
    assert stored == {"request.json", "response.json"}, "os dois lados da conversa são o registro auditável"
    assert all(call["Bucket"] == "test-bucket" for call in fake_client.put_calls)

    db_session = correction_job_fixture.db_session
    attempts_query = select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)
    attempts = (await db_session.execute(attempts_query)).scalars().all()
    assert len(attempts) == 1
    assert attempts[0].raw_request_ref is not None and attempts[0].raw_request_ref.endswith("request.json")
    assert attempts[0].raw_response_ref is not None and attempts[0].raw_response_ref.endswith("response.json")


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


@pytest.mark.asyncio
async def test_attempt_grava_cache_custo_provedor_e_vereditos(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()

    class ProviderComCache:
        model_id = "openrouter:modelo/teste"

        async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
            return ProviderResponse(
                raw_text="{}",
                structured=CorrectionCandidate.model_validate(
                    {
                        "scores": {c: {"nota": 7, "justificativa": f"ok {c}"} for c in FIXED_CRITERIA},
                        "feedback": "ok",
                        "sugestao_acionavel": "revise",
                    }
                ),
                tokens_in=100,
                tokens_out=20,
                latency_ms=10,
                cache_read_tokens=900,
                cache_write_tokens=50,
                cost_usd=Decimal("0.00012345"),
                served_provider="anthropic",
                model_retries=1,
                guardrail_events=[{"guard": "citacoes", "veredito": "retry", "motivo": "citacao ausente: x"}],
            )

    await correction_job_fixture.process(municipio, job, provider=ProviderComCache())

    db_session = correction_job_fixture.db_session
    attempt = (
        (await db_session.execute(select(CorrectionAttempt).where(CorrectionAttempt.correction_job_id == job.uuid)))
        .scalars()
        .one()
    )
    assert attempt.tokens_in == 100
    assert attempt.cache_read_tokens == 900
    assert attempt.cache_write_tokens == 50
    assert attempt.cost_usd == Decimal("0.00012345")
    assert attempt.served_provider == "anthropic"
    assert attempt.model_retries == 1
    assert attempt.guardrail_events[0]["guard"] == "citacoes"


@pytest.mark.asyncio
async def test_transcricao_insuficiente_falha_o_job_sem_chamar_o_corretor(correction_job_fixture):
    municipio, job = await correction_job_fixture.build(
        input_type="image", raw_text=None, original_ref="submissions/teste/original.png"
    )
    await correction_job_fixture.storage.put(
        key="submissions/teste/original.png", content=b"\x89PNG falso", content_type="image/png"
    )

    class OCRQueFalha:
        async def extract_text(self, image_bytes: bytes) -> OCRResult:
            raise TranscriptionQualityError("transcricao insuficiente")

    class ProviderQueNaoDeveRodar:
        model_id = "openrouter:modelo/teste"

        async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
            raise AssertionError("o corretor nao pode rodar com transcricao insuficiente")

    with pytest.raises(TranscriptionQualityError):
        await correction_job_fixture.process(municipio, job, provider=ProviderQueNaoDeveRodar(), ocr_provider=OCRQueFalha())

    db_session = correction_job_fixture.db_session
    await db_session.refresh(job)
    assert job.status == "failed"


@pytest.mark.asyncio
async def test_transcricao_com_falha_de_qualidade_deixa_rastro_na_submissao(correction_job_fixture):
    """Uma folha ilegivel tem que chegar a um humano com o rastro de quanto custou tentar le-la.

    Sem isso, o manifesto mostra `transcription: null` para exatamente o caso que mais precisa de
    auditoria: a folha que falhou a checagem de qualidade apos chamadas reais ao modelo.
    """
    municipio, job = await correction_job_fixture.build(
        input_type="image", raw_text=None, original_ref="submissions/rastro-falha/original.png"
    )
    await correction_job_fixture.storage.put(
        key="submissions/rastro-falha/original.png", content=b"\x89PNG falso", content_type="image/png"
    )

    class OCRQueFalhaComRastro:
        async def extract_text(self, image_bytes: bytes) -> OCRResult:
            raise TranscriptionQualityError(
                "transcricao insuficiente",
                partial_meta={"model": "openrouter:modelo/teste", "tokens_in": 1000, "tokens_out": 200},
            )

    class ProviderQueNaoDeveRodar:
        model_id = "openrouter:modelo/teste"

        async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
            raise AssertionError("o corretor nao pode rodar com transcricao insuficiente")

    with pytest.raises(TranscriptionQualityError):
        await correction_job_fixture.process(
            municipio, job, provider=ProviderQueNaoDeveRodar(), ocr_provider=OCRQueFalhaComRastro()
        )

    db_session = correction_job_fixture.db_session
    await db_session.refresh(job)
    assert job.status == "failed"

    submission = (await db_session.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalar_one()
    assert submission.transcription_meta["error"] == "transcricao insuficiente"
    assert submission.transcription_meta["tokens_in"] == 1000
    assert submission.transcription_meta["tokens_out"] == 200


@pytest.mark.asyncio
async def test_transcricao_deixa_rastro_na_submissao(correction_job_fixture):
    municipio, job = await correction_job_fixture.build(
        input_type="image", raw_text=None, original_ref="submissions/rastro/original.png"
    )
    await correction_job_fixture.storage.put(
        key="submissions/rastro/original.png", content=b"\x89PNG falso", content_type="image/png"
    )

    await correction_job_fixture.process(municipio, job)

    db_session = correction_job_fixture.db_session
    submission = (await db_session.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalars().one()
    assert submission.transcription_meta["model"] == "mock"
    assert submission.raw_text
