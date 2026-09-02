from pydantic import BaseModel, ConfigDict, Field

from app.schemas.form_builder.form_question_config import FormQuestionConfig


class FormQuestionCreate(BaseModel):
    question_definition_id: int = Field(
        gt=0,
    )

    question_version_id: int = Field(
        gt=0,
    )

    config: FormQuestionConfig = Field(
        default_factory=FormQuestionConfig,
    )


class FormQuestionUpdate(BaseModel):
    config: FormQuestionConfig | None = None


class FormQuestionOptionResponse(BaseModel):
    id: int
    value: str
    label: str
    position: int
    option_metadata: dict

    model_config = ConfigDict(
        from_attributes=True,
    )


class FormQuestionResponse(BaseModel):
    id: int
    form_id: int
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

    options: list[FormQuestionOptionResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


class FormQuestionListResponse(BaseModel):
    items: list[FormQuestionResponse]
    count: int


class FormQuestionReorder(BaseModel):
    ordered_question_ids: list[int] = Field(
        min_length=1,
    )
