from pydantic import BaseModel, ConfigDict, Field


class ProjectSectionCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    config: dict = Field(
        default_factory=dict,
    )


class ProjectSectionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    config: dict | None = None


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
