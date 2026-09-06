"""O cadeado do Swagger so aparece quando a dependencia de auth e um SecurityBase.

Lendo o header/cookie com Header()/Cookie() a auth vira parametro comum: o
schema nao ganha securitySchemes, nenhuma rota ganha `security`, e o botao
Authorize some.
"""

import pytest

from src.interfaces.main import app

API_KEY_ROUTE = ("/api/v1/aes/models", "get")
SESSION_ROUTE = ("/api/v1/users/me", "get")


@pytest.fixture
def schema() -> dict:
    app.openapi_schema = None
    return app.openapi()


def _operation(schema: dict, route: tuple[str, str]) -> dict:
    path, method = route
    return schema["paths"][path][method]


def test_security_schemes_are_declared(schema: dict) -> None:
    schemes = schema["components"]["securitySchemes"]
    assert schemes["APIKeyHeader"] == {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    assert schemes["SessionCookie"] == {"type": "apiKey", "in": "cookie", "name": "session_id"}


@pytest.mark.parametrize(
    ("route", "scheme"),
    [(API_KEY_ROUTE, "APIKeyHeader"), (SESSION_ROUTE, "SessionCookie")],
)
def test_protected_routes_carry_security(schema: dict, route: tuple[str, str], scheme: str) -> None:
    security = _operation(schema, route).get("security", [])
    assert any(scheme in requirement for requirement in security), f"{route} sem {scheme}: {security}"


def test_credentials_are_not_plain_parameters(schema: dict) -> None:
    names = {p["name"] for p in _operation(schema, API_KEY_ROUTE).get("parameters", [])}
    assert "X-API-Key" not in names
