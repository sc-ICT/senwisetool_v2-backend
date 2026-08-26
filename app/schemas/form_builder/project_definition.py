from pydantic import BaseModel, ConfigDict, Field

from app.models.form_builder.enums import ProjectStatus


class ProjectDefinitionCreate(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    project_type: str = Field(
        min_length=1,
        max_length=100,
    )

    global_config: dict = Field(
        default_factory=dict,
    )


class ProjectDefinitionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    project_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    global_config: dict | None = None

    status: ProjectStatus | None = None


class ProjectDefinitionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    project_type: str
    status: ProjectStatus
    global_config: dict
    created_by: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProjectDefinitionListResponse(BaseModel):
    items: list[ProjectDefinitionResponse]
    count: int
