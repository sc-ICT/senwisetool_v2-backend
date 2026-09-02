from pydantic import BaseModel, ConfigDict, Field

from app.schemas.form_builder.section_repeat import SectionRepeatConfig


class FormSectionConfig(BaseModel):
    repeat: SectionRepeatConfig = Field(
        default_factory=SectionRepeatConfig,
    )

    model_config = ConfigDict(
        extra="allow",
    )


class FormSectionCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    config: FormSectionConfig = Field(
        default_factory=FormSectionConfig,
    )


class FormSectionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    config: FormSectionConfig | None = None


class FormSectionResponse(BaseModel):
    id: int
    form_id: int
    name: str
    description: str | None
    position: int
    config: dict

    model_config = ConfigDict(
        from_attributes=True,
    )


class FormSectionListResponse(BaseModel):
    items: list[FormSectionResponse]
    count: int


class FormSectionReorder(BaseModel):
    ordered_section_ids: list[int] = Field(
        min_length=1,
    )
