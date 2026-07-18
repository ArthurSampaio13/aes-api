from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..providers.base import FIXED_CRITERIA


class CriterionDefinition(BaseModel):
    descricao: str
    peso: float = Field(gt=0, le=1)
    escala_max: int = Field(gt=0)


class RubricCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    municipio_id: int | None = None
    version: Annotated[int, Field(ge=1)]
    criteria: dict[str, CriterionDefinition]

    @model_validator(mode="after")
    def require_all_fixed_criteria(self) -> "RubricCreate":
        missing = set(FIXED_CRITERIA) - set(self.criteria.keys())
        if missing:
            raise ValueError(f"Missing required criteria: {sorted(missing)}")
        return self


class RubricRead(BaseModel):
    id: int
    municipio_id: int | None
    version: int
    criteria: dict[str, CriterionDefinition]
