from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..common.exceptions import ResourceNotFoundError
from .crud import crud_essay_prompts, crud_prompt_templates, crud_rubrics
from .models.correction import CorrectionJob
from .models.submission import Batch, Submission
from .schemas.essay_prompt import EssayPromptCreate, EssayPromptRead
from .schemas.rubric import RubricCreate, RubricRead
from .schemas.submission import BatchSubmitRequest
from .worker import run_correction_job


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

    async def submit_batch(
        self, data: BatchSubmitRequest, user_id: int, municipio_id: int, db: AsyncSession
    ) -> tuple[Any, list[Any]]:
        essay_prompt = await self.get_essay_prompt(str(data.essay_prompt_uuid), db)

        batch = Batch(municipio_id=municipio_id, essay_prompt_id=essay_prompt["uuid"], created_by_user_id=user_id)
        db.add(batch)
        await db.flush()

        job_ids = []
        for text in data.texts:
            submission = Submission(
                municipio_id=municipio_id,
                batch_id=batch.uuid,
                input_type="text",
                original_ref="",
                raw_text=text,
            )
            db.add(submission)
            await db.flush()

            job = CorrectionJob(
                municipio_id=municipio_id,
                submission_id=submission.uuid,
                provider=data.provider,
                model=data.model,
                status="pending",
            )
            db.add(job)
            await db.flush()
            job_ids.append(job.uuid)

        await db.commit()

        for job_id in job_ids:
            await run_correction_job.kiq(  # type: ignore[call-overload]
                job_id=str(job_id), prompt_text="Corrija: {essay_text}", prompt_version=1, rubric_version=1
            )

        return batch.uuid, job_ids
