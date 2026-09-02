from pydantic import BaseModel, Field


class FormQuestionValidationConfig(BaseModel):
    required: bool = False

    min_value: float | None = None
    max_value: float | None = None

    min_length: int | None = Field(
        default=None,
        ge=0,
    )

    max_length: int | None = Field(
        default=None,
        ge=0,
    )

    default_value: str | list[str] | None = None


class FormQuestionDisplayConfig(BaseModel):
    visible: bool = True
    readonly: bool = False

    placeholder: str | None = None
    help_text: str | None = None


class FormQuestionConfig(BaseModel):
    validation: FormQuestionValidationConfig = Field(
        default_factory=FormQuestionValidationConfig,
    )

    display: FormQuestionDisplayConfig = Field(
        default_factory=FormQuestionDisplayConfig,
    )
