from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..common.exceptions import BudgetExceededError, ResourceNotFoundError
from ..municipio.crud import crud_municipios
from .crud import crud_correction_jobs, crud_correction_results, crud_essay_prompts, crud_prompt_templates, crud_rubrics
from .models.correction import CorrectionAttempt, CorrectionJob
from .models.submission import Batch, Submission
from .schemas.essay_prompt import EssayPromptCreate, EssayPromptRead
from .schemas.rubric import RubricCreate, RubricRead
from .schemas.submission import BatchSubmitRequest, JobResultRead
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

    async def check_budget(self, municipio_id: int, db: AsyncSession) -> None:
        municipio = await crud_municipios.get(db=db, id=municipio_id)
        if not municipio or municipio["monthly_token_budget"] is None:
            return

        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spend = await db.execute(
            select(func.coalesce(func.sum(CorrectionAttempt.tokens_in + CorrectionAttempt.tokens_out), 0)).where(
                CorrectionAttempt.municipio_id == municipio_id, CorrectionAttempt.created_at >= month_start
            )
        )
        total_tokens = spend.scalar_one()
        if total_tokens >= municipio["monthly_token_budget"]:
            raise BudgetExceededError(
                f"Municipio {municipio_id} has used {total_tokens} tokens this month, "
                f"at or above the {municipio['monthly_token_budget']} token budget."
            )

    async def submit_batch(
        self, data: BatchSubmitRequest, user_id: int, municipio_id: int, db: AsyncSession
    ) -> tuple[Any, list[Any]]:
        await self.check_budget(municipio_id, db)
        essay_prompt = await self.get_essay_prompt(str(data.essay_prompt_uuid), db)
        prompt_template = await crud_prompt_templates.get(db=db, id=essay_prompt["prompt_template_id"])
        rubric = await crud_rubrics.get(db=db, id=essay_prompt["rubric_id"])

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
                job_id=str(job_id),
                municipio_id=municipio_id,
                prompt_text=prompt_template["template_text"],  # type: ignore[index]
                prompt_version=prompt_template["version"],  # type: ignore[index]
                rubric_version=rubric["version"],  # type: ignore[index]
            )

        return batch.uuid, job_ids

    async def get_job_status(self, job_id: str, db: AsyncSession) -> dict[str, Any]:
        job = await crud_correction_jobs.get(db=db, uuid=job_id)
        if not job:
            raise ResourceNotFoundError(f"Job {job_id} not found")
        return {"job_id": job["uuid"], "status": job["status"], "provider": job["provider"], "model": job["model"]}

    async def get_job_result(self, job_id: str, db: AsyncSession) -> dict[str, Any]:
        result = await crud_correction_results.get(db=db, correction_job_id=job_id, schema_to_select=JobResultRead)
        if not result:
            raise ResourceNotFoundError(f"Result for job {job_id} not found (job may not be done yet)")
        return result
