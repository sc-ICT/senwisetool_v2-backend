from typing import Literal

from pydantic import BaseModel, Field

DependencyOperator = Literal[
    "EQUALS",
    "NOT_EQUALS",
    "IN",
    "NOT_IN",
]


class ProjectQuestionDependencyCreate(BaseModel):
    source_question_id: int = Field(
        gt=0,
    )

    operator: DependencyOperator

    value: str = Field(
        min_length=1,
        max_length=500,
    )


class ProjectQuestionDependencyResponse(BaseModel):
    id: int

    target_question_id: int
    source_question_id: int

    operator: DependencyOperator
    value: str

    model_config = {
        "from_attributes": True,
    }
