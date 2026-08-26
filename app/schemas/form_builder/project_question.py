from pydantic import BaseModel, ConfigDict, Field

from app.schemas.form_builder.project_question_config import ProjectQuestionConfig


class ProjectQuestionCreate(BaseModel):
    question_definition_id: int = Field(
        gt=0,
    )

    question_version_id: int = Field(
        gt=0,
    )

    config: ProjectQuestionConfig = Field(
        default_factory=ProjectQuestionConfig,
    )


class ProjectQuestionUpdate(BaseModel):
    config: ProjectQuestionConfig | None = None


class ProjectQuestionOptionResponse(BaseModel):
    id: int
    value: str
    label: str
    position: int
    option_metadata: dict

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProjectQuestionResponse(BaseModel):
    id: int
    project_id: int
    section_id: int
    question_definition_id: int
    question_version_id: int
    position: int
    config: dict

    question_code: str
    question_name: str

    version_number: int
    version_label: str
    question_type: str

    options: list[ProjectQuestionOptionResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProjectQuestionListResponse(BaseModel):
    items: list[ProjectQuestionResponse]
    count: int


class ProjectQuestionReorder(BaseModel):
    ordered_question_ids: list[int] = Field(
        min_length=1,
    )
