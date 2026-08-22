from pydantic import BaseModel, ConfigDict, Field

from app.models.form_builder.enums import QuestionGroupStatus


class QuestionGroupCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None


class QuestionGroupUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    status: QuestionGroupStatus | None = None


class QuestionGroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: QuestionGroupStatus
    created_by: int
    question_ids: list[int] = []

    model_config = ConfigDict(
        from_attributes=True,
    )


class QuestionGroupListResponse(BaseModel):
    items: list[QuestionGroupResponse]
    count: int


class QuestionGroupQuestionResponse(BaseModel):
    id: int
    code: str
    name: str
    status: str

    model_config = ConfigDict(
        from_attributes=True,
    )


class QuestionGroupDetailResponse(QuestionGroupResponse):
    questions: list[QuestionGroupQuestionResponse]
