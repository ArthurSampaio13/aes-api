"""Catálogo de modelos do OpenRouter, usado para listar e para validar o job."""

from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel

CATALOG_URL = "https://openrouter.ai/api/v1/models"


class ModelInfo(BaseModel):
    id: str
    input_modalities: list[str]
    prompt_price: float
    completion_price: float


def _default_client_factory() -> Any:
    return httpx.AsyncClient(timeout=20.0)


async def fetch_catalog(client_factory: Callable[[], Any] | None = None) -> dict[str, ModelInfo]:
    factory = client_factory or _default_client_factory
    async with factory() as client:
        response = await client.get(CATALOG_URL)
        response.raise_for_status()
        payload = response.json()

    catalogo: dict[str, ModelInfo] = {}
    for entry in payload["data"]:
        pricing = entry.get("pricing") or {}
        catalogo[entry["id"]] = ModelInfo(
            id=entry["id"],
            input_modalities=(entry.get("architecture") or {}).get("input_modalities") or [],
            prompt_price=float(pricing.get("prompt") or 0),
            completion_price=float(pricing.get("completion") or 0),
        )
    return catalogo
