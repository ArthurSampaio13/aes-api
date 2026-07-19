from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pyfiglet
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from ..infrastructure.app_factory import create_application, lifespan_factory
from ..infrastructure.config.settings import get_settings
from ..infrastructure.logging import configure_logging
from ..infrastructure.security import validate_production_security
from ..interfaces.api import router
from .admin.initialize import create_admin_interface

settings = get_settings()


@asynccontextmanager
async def lifespan_with_security(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan that includes security validation."""
    print(pyfiglet.figlet_format("AES-API"))
    configure_logging()

    if settings.PRODUCTION_SECURITY_VALIDATION_ENABLED:
        validate_production_security(settings)

    default_lifespan = lifespan_factory(settings)

    async with default_lifespan(app):
        yield


app = create_application(
    router=router,
    settings=settings,
    lifespan=lifespan_with_security,
    create_tables_on_startup=None,
    enable_cors=None,
    cors_origins=None,
    enable_docs_in_production=None,
    docs_production_dependency=None,
    enable_gzip=None,
    openapi_prefix=None,
    title="AES-API",
    summary="Assistive LLM-based essay correction for Ensino Fundamental",
    description="""
    # AES-API

    A rubric-based, traceable essay-correction backend for Brazilian Ensino Fundamental, built as a TCC artifact.

    * Asynchronous batch correction jobs with configurable, versioned rubrics and prompts
    * LLM provider abstraction (OpenRouter, Amazon Bedrock) with schema-validated structured output
    * Multi-tenant per-município data isolation via PostgreSQL RLS
    """,
    version="0.18.0",
    contact=None,
    license_info={
        "name": "MIT",
        "identifier": "MIT",
    },
    openapi_tags=None,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
create_admin_interface(app)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy"}
