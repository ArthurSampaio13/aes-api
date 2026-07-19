from src.modules.municipio.models import Municipio


def test_municipio_has_expected_columns():
    municipio = Municipio(nome="Garanhuns", monthly_token_budget=1_000_000)
    assert municipio.nome == "Garanhuns"
    assert municipio.monthly_token_budget == 1_000_000


def test_municipio_budget_defaults_to_none():
    municipio = Municipio(nome="Sem limite")
    assert municipio.monthly_token_budget is None
