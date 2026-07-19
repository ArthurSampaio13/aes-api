import pytest

from src.modules.aes.models.rubric import PromptTemplate
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
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


@pytest.mark.asyncio
async def test_job_status_then_results_after_worker_runs(auth_client, db_session, test_user):
    municipio = Municipio(nome="Job Status Test")
    db_session.add(municipio)
    await db_session.commit()
    test_user["municipio_id"] = municipio.id

    criteria = {c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA}
    rubric_resp = await auth_client.post("/api/v1/aes/rubrics", json={"version": 1, "criteria": criteria})
    template = PromptTemplate(municipio_id=municipio.id, version=1, template_text="Corrija: {essay_text}")
    db_session.add(template)
    await db_session.commit()
    prompt_resp = await auth_client.post(
        "/api/v1/aes/essay-prompts",
        json={
            "titulo": "Teste",
            "enunciado": "Escreva sobre...",
            "ano_escolar": "9",
            "genero_textual": "dissertativo-argumentativo",
            "support_texts": [],
            "rubric_id": rubric_resp.json()["id"],
            "prompt_template_id": template.id,
        },
    )

    submit_resp = await auth_client.post(
        "/api/v1/aes/jobs",
        json={
            "essay_prompt_uuid": prompt_resp.json()["uuid"],
            "texts": ["Texto de teste."],
            "provider": "mock",
            "model": "mock-v1",
        },
    )
    job_id = submit_resp.json()["job_ids"][0]

    await process_correction_job(
        job_id=job_id,
        municipio_id=municipio.id,
        db=db_session,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client()),
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    status_resp = await auth_client.get(f"/api/v1/aes/jobs/{job_id}")
    assert status_resp.json()["status"] == "done"

    results_resp = await auth_client.get(f"/api/v1/aes/jobs/{job_id}/results")
    assert results_resp.status_code == 200
    assert results_resp.json()["requires_teacher_review"] is True
