from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.auth.api_key_dependencies import get_current_principal
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.cache import cache
from ...infrastructure.config.settings import get_settings
from ...modules.api_keys.enums import KeyPermissionAction, KeyPermissionResource
from ..common.utils.error_handler import handle_exception
from .dependencies import AesServiceDep, get_aes_tenant_session
from .providers.registry import PROVIDER_FACTORIES
from .schemas.essay_prompt import EssayPromptCreate, EssayPromptRead
from .schemas.rubric import RubricCreate, RubricRead
from .schemas.submission import BatchSubmitRequest, BatchSubmitResponse, JobResultRead, JobStatusRead, ModelInfo
from .storage import ObjectStorage, get_object_storage

router = APIRouter(tags=["AES"])

_rubric_write = get_current_principal(KeyPermissionResource.RUBRICS, KeyPermissionAction.CREATE)
_rubric_read = get_current_principal(KeyPermissionResource.RUBRICS, KeyPermissionAction.READ)
_essay_prompt_write = get_current_principal(KeyPermissionResource.ESSAY_PROMPTS, KeyPermissionAction.CREATE)
_essay_prompt_read = get_current_principal(KeyPermissionResource.ESSAY_PROMPTS, KeyPermissionAction.READ)
_batch_write = get_current_principal(KeyPermissionResource.BATCHES, KeyPermissionAction.CREATE)
_batch_read = get_current_principal(KeyPermissionResource.BATCHES, KeyPermissionAction.READ)


def _municipio_id_from_principal(
    principal_dependency: Callable[..., Awaitable[dict[str, Any]]],
) -> Callable[..., Awaitable[int]]:
    """Extract `municipio_id` as its own bare dependency, for the `@cache` decorator's `{municipio_id}` key
    interpolation (Task 2b) — must be passed the same `principal_dependency` object used for the route's `db`/
    `current_user` dependencies so FastAPI's per-request cache resolves it only once, not three times."""

    async def _extract(current_user: Annotated[dict[str, Any], Depends(principal_dependency)]) -> int:
        return current_user["municipio_id"]  # type: ignore[no-any-return]

    return _extract


_rubric_read_municipio_id = _municipio_id_from_principal(_rubric_read)
_essay_prompt_read_municipio_id = _municipio_id_from_principal(_essay_prompt_read)


@router.post("/rubrics", status_code=201, response_model=RubricRead)
async def create_rubric(
    data: RubricCreate,
    db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_rubric_write))],
    current_user: Annotated[dict[str, Any], Depends(_rubric_write)],
    aes_service: AesServiceDep,
) -> dict[str, Any]:
    try:
        return await aes_service.create_rubric(data, municipio_id=current_user["municipio_id"], db=db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/rubrics/{rubric_id}", response_model=RubricRead)
@cache(key_prefix="aes_rubric:{municipio_id}", resource_id_name="rubric_id", expiration=3600)
async def get_rubric(
    request: Request,
    rubric_id: int,
    municipio_id: Annotated[int, Depends(_rubric_read_municipio_id)],
    db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_rubric_read))],
    aes_service: AesServiceDep,
) -> dict[str, Any]:
    try:
        return await aes_service.get_rubric(rubric_id, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    current_user: Annotated[dict[str, Any], Depends(_rubric_read)],
) -> list[dict[str, Any]]:
    settings = get_settings()
    configured = {
        "mock": ("mock", True),
        "openrouter": (settings.OPENROUTER_MODEL, bool(settings.OPENROUTER_API_KEY)),
        "bedrock": (settings.BEDROCK_MODEL_ID, True),
    }
    return [{"provider": name, "model": configured[name][0], "available": configured[name][1]} for name in PROVIDER_FACTORIES]


@router.post("/essay-prompts", status_code=201, response_model=EssayPromptRead)
async def create_essay_prompt(
    data: EssayPromptCreate,
    db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_essay_prompt_write))],
    current_user: Annotated[dict[str, Any], Depends(_essay_prompt_write)],
    aes_service: AesServiceDep,
) -> dict[str, Any]:
    try:
        return await aes_service.create_essay_prompt(data, municipio_id=current_user["municipio_id"], db=db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/essay-prompts/{essay_prompt_uuid}", response_model=EssayPromptRead)
@cache(key_prefix="aes_essay_prompt:{municipio_id}", resource_id_name="essay_prompt_uuid", expiration=3600)
async def get_essay_prompt(
    request: Request,
    essay_prompt_uuid: str,
    municipio_id: Annotated[int, Depends(_essay_prompt_read_municipio_id)],
    db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_essay_prompt_read))],
    aes_service: AesServiceDep,
) -> dict[str, Any]:
    try:
        return await aes_service.get_essay_prompt(essay_prompt_uuid, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/jobs", status_code=201, response_model=BatchSubmitResponse)
async def submit_batch(
    data: BatchSubmitRequest,
    db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_batch_write))],
    current_user: Annotated[dict[str, Any], Depends(_batch_write)],
    aes_service: AesServiceDep,
) -> dict[str, Any]:
    try:
        batch_id, job_ids = await aes_service.submit_batch(
            data, user_id=current_user["id"], municipio_id=current_user["municipio_id"], db=db
        )
        return {"batch_id": batch_id, "job_ids": job_ids}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/jobs/images", status_code=201, response_model=BatchSubmitResponse)
async def submit_image_batch(
    db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_batch_write))],
    current_user: Annotated[dict[str, Any], Depends(_batch_write)],
    aes_service: AesServiceDep,
    object_storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    essay_prompt_uuid: Annotated[str, Form()],
    images: Annotated[list[UploadFile], File()],
    provider: Annotated[str, Form()] = "mock",
    model: Annotated[str, Form()] = "mock-v1",
) -> dict[str, Any]:
    try:
        image_data = [(await image.read(), image.content_type or "") for image in images]
        batch_id, job_ids = await aes_service.submit_image_batch(
            essay_prompt_uuid=essay_prompt_uuid,
            images=image_data,
            provider=provider,
            model=model,
            user_id=current_user["id"],
            municipio_id=current_user["municipio_id"],
            db=db,
            object_storage=object_storage,
        )
        return {"batch_id": batch_id, "job_ids": job_ids}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/jobs/{job_id}", response_model=JobStatusRead)
async def get_job_status(
    job_id: str, db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_batch_read))], aes_service: AesServiceDep
) -> dict[str, Any]:
    try:
        return await aes_service.get_job_status(job_id, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/jobs/{job_id}/results", response_model=JobResultRead)
async def get_job_results(
    job_id: str, db: Annotated[AsyncSession, Depends(get_aes_tenant_session(_batch_read))], aes_service: AesServiceDep
) -> dict[str, Any]:
    try:
        return await aes_service.get_job_result(job_id, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
