import pytest

from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.municipio.models import Municipio


@pytest.fixture
def valid_criteria():
    return {c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA}


@pytest.mark.asyncio
async def test_create_rubric_requires_all_five_fixed_criteria(auth_client, test_user, db_session):
    municipio = Municipio(nome="Garanhuns Teste")
    db_session.add(municipio)
    await db_session.commit()

    invalid_criteria = {"adequacao_tema": {"descricao": "x", "peso": 1.0, "escala_max": 10}}
    response = await auth_client.post(
        "/api/v1/aes/rubrics",
        json={"version": 1, "criteria": invalid_criteria},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_and_get_rubric(auth_client, db_session, test_user, valid_criteria):
    municipio = Municipio(nome="Garanhuns Teste 2")
    db_session.add(municipio)
    await db_session.commit()
    test_user["municipio_id"] = municipio.id

    response = await auth_client.post("/api/v1/aes/rubrics", json={"version": 1, "criteria": valid_criteria})
    assert response.status_code == 201
    rubric_id = response.json()["id"]

    get_response = await auth_client.get(f"/api/v1/aes/rubrics/{rubric_id}")
    assert get_response.status_code == 200
    assert set(get_response.json()["criteria"].keys()) == set(valid_criteria.keys())


@pytest.mark.asyncio
async def test_create_rubric_uses_authenticated_users_municipio_not_request_body(
    auth_client, db_session, test_user, valid_criteria
):
    municipio_a = Municipio(nome="Municipio A Tenant Test")
    municipio_b = Municipio(nome="Municipio B Tenant Test")
    db_session.add_all([municipio_a, municipio_b])
    await db_session.commit()
    test_user["municipio_id"] = municipio_a.id

    response = await auth_client.post("/api/v1/aes/rubrics", json={"version": 1, "criteria": valid_criteria})

    assert response.status_code == 201
    assert response.json()["municipio_id"] == municipio_a.id
