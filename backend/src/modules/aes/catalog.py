"""Catálogo de modelos do OpenRouter, usado para listar e para validar o job.

Cacheado em memória do processo (por pod) com um TTL simples: um dict cacheado mais o instante em que foi buscado. Isso
evita que cada submissão de job (Task 5) ou cada GET /models vire um round-trip à OpenRouter.
"""

import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel

CATALOG_URL = "https://openrouter.ai/api/v1/models"
_CACHE_TTL_SECONDS = 3600


class ModelInfo(BaseModel):
    id: str
    input_modalities: list[str]
    prompt_price: float
    completion_price: float


def _default_client_factory() -> Any:
    return httpx.AsyncClient(timeout=20.0)


_cached_catalog: dict[str, ModelInfo] | None = None
_cached_at: float | None = None


def _reset_cache() -> None:
    global _cached_catalog, _cached_at
    _cached_catalog = None
    _cached_at = None


async def fetch_catalog(client_factory: Callable[[], Any] | None = None) -> dict[str, ModelInfo]:
    global _cached_catalog, _cached_at
    now = time.monotonic()
    if _cached_catalog is not None and _cached_at is not None and now - _cached_at < _CACHE_TTL_SECONDS:
        return _cached_catalog

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
    _cached_catalog = catalogo
    _cached_at = now
    return catalogo
