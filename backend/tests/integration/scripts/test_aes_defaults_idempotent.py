import pytest
from sqlalchemy import func, select

from scripts.create_aes_defaults import create_aes_defaults
from scripts.create_bootstrap_api_key import BOOTSTRAP_KEY_NAME, BOOTSTRAP_PERMISSIONS, ensure_bootstrap_api_key
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.api_keys.models import APIKey, KeyPermission
from src.modules.municipio.models import Municipio
from src.modules.user.models import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_defaults_are_created_once(rls_db_real_commits):
    await create_aes_defaults(rls_db_real_commits)
    await create_aes_defaults(rls_db_real_commits)

    for model in (Municipio, Rubric, PromptTemplate):
        count = (await rls_db_real_commits.execute(select(func.count()).select_from(model))).scalar_one()
        assert count == 1, f"{model.__name__} was duplicated on the second run"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_default_rubric_has_the_five_fixed_criteria(rls_db_real_commits):
    await create_aes_defaults(rls_db_real_commits)

    rubric = (await rls_db_real_commits.execute(select(Rubric))).scalar_one()
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
async def test_bootstrap_api_key_is_issued_once(rls_db_real_commits, test_superuser):
    municipio, _, _ = await create_aes_defaults(rls_db_real_commits)

    first_key = await ensure_bootstrap_api_key(rls_db_real_commits, municipio.id)
    second_key = await ensure_bootstrap_api_key(rls_db_real_commits, municipio.id)

    assert first_key
    assert second_key is None

    count = (
        await rls_db_real_commits.execute(
            select(func.count())
            .select_from(APIKey)
            .where(APIKey.user_id == test_superuser["id"], APIKey.name == BOOTSTRAP_KEY_NAME)
        )
    ).scalar_one()
    assert count == 1

    api_key = (
        await rls_db_real_commits.execute(
            select(APIKey).where(APIKey.user_id == test_superuser["id"], APIKey.name == BOOTSTRAP_KEY_NAME)
        )
    ).scalar_one()
    granted = (
        (await rls_db_real_commits.execute(select(KeyPermission).where(KeyPermission.api_key_id == api_key.id))).scalars().all()
    )
    granted_pairs = {(p.resource.value, p.action.value) for p in granted}
    expected_pairs = {(resource, action) for resource, actions in BOOTSTRAP_PERMISSIONS.items() for action in actions}
    assert granted_pairs == expected_pairs


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_api_key_binds_superuser_to_demo_municipio(rls_db_real_commits, test_superuser):
    municipio, _, _ = await create_aes_defaults(rls_db_real_commits)

    await ensure_bootstrap_api_key(rls_db_real_commits, municipio.id)

    user = (await rls_db_real_commits.execute(select(User).where(User.id == test_superuser["id"]))).scalar_one()
    assert user.municipio_id == municipio.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_api_key_returns_none_without_a_superuser(rls_db_real_commits):
    municipio, _, _ = await create_aes_defaults(rls_db_real_commits)

    result = await ensure_bootstrap_api_key(rls_db_real_commits, municipio.id)

    assert result is None
