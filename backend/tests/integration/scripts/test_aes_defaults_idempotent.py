import pytest
from sqlalchemy import func, select

from scripts.create_aes_defaults import create_aes_defaults
from scripts.create_bootstrap_api_key import BOOTSTRAP_KEY_NAME, ensure_bootstrap_api_key
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.api_keys.models import APIKey
from src.modules.municipio.models import Municipio
from src.modules.user.models import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_defaults_are_created_once(test_db):
    await create_aes_defaults(test_db)
    await create_aes_defaults(test_db)

    for model in (Municipio, Rubric, PromptTemplate):
        count = (await test_db.execute(select(func.count()).select_from(model))).scalar_one()
        assert count == 1, f"{model.__name__} was duplicated on the second run"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_default_rubric_has_the_five_fixed_criteria(test_db):
    await create_aes_defaults(test_db)

    rubric = (await test_db.execute(select(Rubric))).scalar_one()
    assert set(rubric.criteria) == {
        "adequacao_tema",
        "estrutura_textual",
        "coesao_coerencia",
        "adequacao_ling",
        "vocabulario",
    }
    assert rubric.municipio_id is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_api_key_is_issued_once(test_db, test_superuser):
    municipio, _, _ = await create_aes_defaults(test_db)

    first_key = await ensure_bootstrap_api_key(test_db, municipio.id)
    second_key = await ensure_bootstrap_api_key(test_db, municipio.id)

    assert first_key
    assert second_key is None

    count = (
        await test_db.execute(
            select(func.count())
            .select_from(APIKey)
            .where(APIKey.user_id == test_superuser["id"], APIKey.name == BOOTSTRAP_KEY_NAME)
        )
    ).scalar_one()
    assert count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_api_key_binds_superuser_to_demo_municipio(test_db, test_superuser):
    municipio, _, _ = await create_aes_defaults(test_db)

    await ensure_bootstrap_api_key(test_db, municipio.id)

    user = (await test_db.execute(select(User).where(User.id == test_superuser["id"]))).scalar_one()
    assert user.municipio_id == municipio.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_api_key_returns_none_without_a_superuser(test_db):
    municipio, _, _ = await create_aes_defaults(test_db)

    result = await ensure_bootstrap_api_key(test_db, municipio.id)

    assert result is None
