"""O Swagger so desenha o seletor de arquivo quando ve `format: binary`.

O FastAPI emite OpenAPI 3.1, onde um upload vira `contentMediaType:
application/octet-stream` sem `format` — e o widget degrada para uma caixa de
texto, deixando a rota inutilizavel pela interface.
"""

import pytest

from src.interfaces.main import app

UPLOAD_ROUTE = ("/api/v1/aes/jobs/images", "post")


@pytest.fixture
def schema() -> dict:
    app.openapi_schema = None
    return app.openapi()


def _body_schema(schema: dict) -> dict:
    path, method = UPLOAD_ROUTE
    ref = schema["paths"][path][method]["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    return schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def test_upload_field_is_marked_binary(schema: dict) -> None:
    images = _body_schema(schema)["properties"]["images"]
    assert images["type"] == "array", "varios arquivos por requisicao"
    assert images["items"].get("format") == "binary", images["items"]


def test_upload_route_still_accepts_many_files(schema: dict) -> None:
    body = _body_schema(schema)
    assert "images" in body["required"]
    assert body["properties"]["images"]["items"]["contentMediaType"] == "application/octet-stream"
