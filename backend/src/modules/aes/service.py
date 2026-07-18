from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..common.exceptions import ResourceNotFoundError
from .crud import crud_rubrics
from .schemas.rubric import RubricCreate, RubricRead


class AesService:
    async def create_rubric(self, data: RubricCreate, db: AsyncSession) -> dict[str, Any]:
        return await crud_rubrics.create(db=db, object=data, schema_to_select=RubricRead)

    async def get_rubric(self, rubric_id: int, db: AsyncSession) -> dict[str, Any]:
        rubric = await crud_rubrics.get(db=db, id=rubric_id, schema_to_select=RubricRead)
        if not rubric:
            raise ResourceNotFoundError(f"Rubric {rubric_id} not found")
        return rubric
