"""A tentativa registra o modelo que rodou, não o que a requisição pediu.

Quando o job omite o modelo, quem decide é o default do provider. Gravar
`job.model` nesse caso registraria vazio — ou pior, um valor que ninguém usou.
"""

import pytest

from src.modules.aes.providers.registry import PROVIDER_FACTORIES, get_provider


@pytest.mark.parametrize("nome", sorted(PROVIDER_FACTORIES))
def test_every_provider_reports_the_model_it_resolved(nome: str) -> None:
    assert get_provider(nome).model_id, f"{nome} não expõe model_id"


@pytest.mark.parametrize("nome", ["openrouter", "bedrock", "groq"])
def test_the_reported_model_is_the_one_asked_for(nome: str) -> None:
    assert get_provider(nome, "deepseek/deepseek-v4.1-flash").model_id == "deepseek/deepseek-v4.1-flash"
