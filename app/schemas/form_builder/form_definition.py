from pydantic import BaseModel, ConfigDict, Field

from app.models.form_builder.enums import FormStatus


class FormDefinitionCreate(BaseModel):
    project_id: int

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    form_type: str = Field(
        min_length=1,
        max_length=100,
    )


class FormDefinitionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    form_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    global_config: dict | None = None

    status: FormStatus | None = None


class FormDefinitionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    form_type: str
    status: FormStatus
    global_config: dict
    created_by: int
    project_id: int
    form_folder_id: int | None

    model_config = ConfigDict(
        from_attributes=True,
    )


class FormDefinitionListResponse(BaseModel):
    items: list[FormDefinitionResponse]
    count: int


class ProjectFormCreate(BaseModel):
    name: str
    description: str | None = None
    form_type: str
