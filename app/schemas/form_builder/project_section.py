from pydantic import BaseModel, ConfigDict, Field

from app.schemas.form_builder.section_repeat import SectionRepeatConfig


class ProjectSectionConfig(BaseModel):
    repeat: SectionRepeatConfig = Field(
        default_factory=SectionRepeatConfig,
    )

    model_config = ConfigDict(
        extra="allow",
    )


class ProjectSectionCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    config: ProjectSectionConfig = Field(
        default_factory=ProjectSectionConfig,
    )


class ProjectSectionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    config: ProjectSectionConfig | None = None


class ProjectSectionResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None
    position: int
    config: dict

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProjectSectionListResponse(BaseModel):
    items: list[ProjectSectionResponse]
    count: int


class ProjectSectionReorder(BaseModel):
    ordered_section_ids: list[int] = Field(
        min_length=1,
    )
