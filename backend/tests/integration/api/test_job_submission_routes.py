import pytest

from src.modules.aes import service as service_module
from src.modules.aes.models.rubric import PromptTemplate
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.municipio.models import Municipio


async def _create_essay_prompt(auth_client, db_session, test_user):
    municipio = Municipio(nome="Garanhuns Jobs")
    db_session.add(municipio)
    await db_session.commit()
    test_user["municipio_id"] = municipio.id

    criteria = {c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA}
    rubric_resp = await auth_client.post(
        "/api/v1/aes/rubrics", json={"municipio_id": municipio.id, "version": 1, "criteria": criteria}
    )
    template = PromptTemplate(municipio_id=municipio.id, version=1, template_text="Corrija: {essay_text}")
    db_session.add(template)
    await db_session.commit()

    prompt_resp = await auth_client.post(
        "/api/v1/aes/essay-prompts",
        json={
            "municipio_id": municipio.id,
            "titulo": "Teste",
            "enunciado": "Escreva sobre...",
            "ano_escolar": "9",
            "genero_textual": "dissertativo-argumentativo",
            "support_texts": [],
            "rubric_id": rubric_resp.json()["id"],
            "prompt_template_id": template.id,
        },
    )
    return prompt_resp.json()["uuid"]


@pytest.mark.asyncio
async def test_submit_batch_creates_one_job_per_text(auth_client, db_session, test_user):
    essay_prompt_uuid = await _create_essay_prompt(auth_client, db_session, test_user)

    response = await auth_client.post(
        "/api/v1/aes/jobs",
        json={
            "essay_prompt_uuid": essay_prompt_uuid,
            "texts": ["Primeira redação de teste.", "Segunda redação de teste."],
            "provider": "mock",
            "model": "mock-v1",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["job_ids"]) == 2


@pytest.mark.asyncio
async def test_submit_batch_resolves_real_prompt_and_rubric_version(auth_client, db_session, test_user, monkeypatch):
    captured = []

    async def capture_kiq(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(service_module.run_correction_job, "kiq", capture_kiq)

    municipio = Municipio(nome="Prompt Resolution Test")
    db_session.add(municipio)
    await db_session.commit()
    test_user["municipio_id"] = municipio.id

    criteria = {c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA}
    rubric_resp = await auth_client.post(
        "/api/v1/aes/rubrics", json={"municipio_id": municipio.id, "version": 3, "criteria": criteria}
    )
    template = PromptTemplate(municipio_id=municipio.id, version=5, template_text="Modelo customizado: {essay_text}")
    db_session.add(template)
    await db_session.commit()

    prompt_resp = await auth_client.post(
        "/api/v1/aes/essay-prompts",
        json={
            "municipio_id": municipio.id,
            "titulo": "Teste",
            "enunciado": "Escreva sobre...",
            "ano_escolar": "9",
            "genero_textual": "dissertativo-argumentativo",
            "support_texts": [],
            "rubric_id": rubric_resp.json()["id"],
            "prompt_template_id": template.id,
        },
    )

    response = await auth_client.post(
        "/api/v1/aes/jobs",
        json={
            "essay_prompt_uuid": prompt_resp.json()["uuid"],
            "texts": ["Uma redação de teste."],
            "provider": "mock",
            "model": "mock-v1",
        },
    )
    assert response.status_code == 201

    assert len(captured) == 1
    assert captured[0]["prompt_text"] == "Modelo customizado: {essay_text}"
    assert captured[0]["prompt_version"] == 5
    assert captured[0]["rubric_version"] == 3
