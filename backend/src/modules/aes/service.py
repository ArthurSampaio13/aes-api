from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..common.exceptions import ResourceNotFoundError
from .crud import crud_essay_prompts, crud_prompt_templates, crud_rubrics
from .schemas.essay_prompt import EssayPromptCreate, EssayPromptRead
from .schemas.rubric import RubricCreate, RubricRead


class AesService:
    async def create_rubric(self, data: RubricCreate, db: AsyncSession) -> dict[str, Any]:
        return await crud_rubrics.create(db=db, object=data, schema_to_select=RubricRead)

    async def get_rubric(self, rubric_id: int, db: AsyncSession) -> dict[str, Any]:
        rubric = await crud_rubrics.get(db=db, id=rubric_id, schema_to_select=RubricRead)
        if not rubric:
            raise ResourceNotFoundError(f"Rubric {rubric_id} not found")
        return rubric

    async def create_essay_prompt(self, data: EssayPromptCreate, db: AsyncSession) -> dict[str, Any]:
        rubric_exists = await crud_rubrics.exists(db=db, id=data.rubric_id)
        if not rubric_exists:
            raise ResourceNotFoundError(f"Rubric {data.rubric_id} not found")
        template_exists = await crud_prompt_templates.exists(db=db, id=data.prompt_template_id)
        if not template_exists:
            raise ResourceNotFoundError(f"PromptTemplate {data.prompt_template_id} not found")
        return await crud_essay_prompts.create(db=db, object=data, schema_to_select=EssayPromptRead)

    async def get_essay_prompt(self, essay_prompt_uuid: str, db: AsyncSession) -> dict[str, Any]:
        prompt = await crud_essay_prompts.get(db=db, uuid=essay_prompt_uuid, schema_to_select=EssayPromptRead)
        if not prompt:
            raise ResourceNotFoundError(f"EssayPrompt {essay_prompt_uuid} not found")
        return prompt
