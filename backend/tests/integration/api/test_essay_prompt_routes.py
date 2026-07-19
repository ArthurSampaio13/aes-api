import pytest

from src.modules.aes.models.rubric import PromptTemplate
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.municipio.models import Municipio


@pytest.mark.asyncio
async def test_create_essay_prompt_with_support_texts(auth_client, db_session, test_user):
    municipio = Municipio(nome="Garanhuns EssayPrompt")
    db_session.add(municipio)
    await db_session.commit()
    test_user["municipio_id"] = municipio.id

    criteria = {c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA}
    rubric_resp = await auth_client.post("/api/v1/aes/rubrics", json={"version": 1, "criteria": criteria})
    rubric_id = rubric_resp.json()["id"]

    template = PromptTemplate(municipio_id=municipio.id, version=1, template_text="Corrija: {essay_text}")
    db_session.add(template)
    await db_session.commit()

    response = await auth_client.post(
        "/api/v1/aes/essay-prompts",
        json={
            "titulo": "A importância da leitura",
            "enunciado": "Escreva um texto dissertativo-argumentativo sobre a importância da leitura.",
            "ano_escolar": "9",
            "genero_textual": "dissertativo-argumentativo",
            "support_texts": [{"titulo": "Texto motivador 1", "conteudo": "Trecho de apoio..."}],
            "rubric_id": rubric_id,
            "prompt_template_id": template.id,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["support_texts"][0]["titulo"] == "Texto motivador 1"

    get_response = await auth_client.get(f"/api/v1/aes/essay-prompts/{body['uuid']}")
    assert get_response.status_code == 200
