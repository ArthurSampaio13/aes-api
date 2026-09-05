import pytest
from sqlalchemy import func, select

from scripts.create_aes_defaults import create_aes_defaults
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.municipio.models import Municipio


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
