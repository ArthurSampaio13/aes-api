from typing import Any

from fastapi import APIRouter

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import CurrentUserDep, TenantSessionDep
from ..common.utils.error_handler import handle_exception
from .dependencies import AesServiceDep
from .schemas.essay_prompt import EssayPromptCreate, EssayPromptRead
from .schemas.rubric import RubricCreate, RubricRead
from .schemas.submission import BatchSubmitRequest, BatchSubmitResponse

router = APIRouter(tags=["AES"])


@router.post("/rubrics", status_code=201, response_model=RubricRead)
async def create_rubric(data: RubricCreate, db: TenantSessionDep, aes_service: AesServiceDep) -> dict[str, Any]:
    try:
        return await aes_service.create_rubric(data, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/rubrics/{rubric_id}", response_model=RubricRead)
async def get_rubric(rubric_id: int, db: TenantSessionDep, aes_service: AesServiceDep) -> dict[str, Any]:
    try:
        return await aes_service.get_rubric(rubric_id, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/essay-prompts", status_code=201, response_model=EssayPromptRead)
async def create_essay_prompt(data: EssayPromptCreate, db: TenantSessionDep, aes_service: AesServiceDep) -> dict[str, Any]:
    try:
        return await aes_service.create_essay_prompt(data, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/essay-prompts/{essay_prompt_uuid}", response_model=EssayPromptRead)
async def get_essay_prompt(essay_prompt_uuid: str, db: TenantSessionDep, aes_service: AesServiceDep) -> dict[str, Any]:
    try:
        return await aes_service.get_essay_prompt(essay_prompt_uuid, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/jobs", status_code=201, response_model=BatchSubmitResponse)
async def submit_batch(
    data: BatchSubmitRequest, db: TenantSessionDep, current_user: CurrentUserDep, aes_service: AesServiceDep
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
