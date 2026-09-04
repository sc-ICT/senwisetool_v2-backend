from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.form_builder.enums import (
    FormStatus,
    ProjectStatus,
)


class MobileProjectFormResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    form_type: str
    status: FormStatus
    global_config: dict[str, Any]

    model_config = ConfigDict(
        from_attributes=True,
    )


class MobileProjectResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    project_type: str
    status: ProjectStatus
    global_config: dict[str, Any]

    published_form_count: int
    assigned_at: datetime

    forms: list[MobileProjectFormResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


class MobileProjectListItemResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    project_type: str
    status: ProjectStatus
    global_config: dict[str, Any]

    published_form_count: int
    assigned_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class MobileProjectListResponse(BaseModel):
    items: list[MobileProjectListItemResponse]
    count: int


# =====================================================================
# SYNC
# =====================================================================


class MobileProjectSyncFormResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    form_type: str
    updated_at: datetime
    hash: str


class MobileProjectSyncFileResponse(BaseModel):
    file_id: int
    name: str
    mime_type: str | None
    extension: str | None
    size: int | None
    updated_at: datetime


class MobileProjectSyncZoneResponse(BaseModel):
    assignment_zone_id: int
    file_id: int
    name: str
    mime_type: str | None
    extension: str | None
    size: int | None
    updated_at: datetime


class MobileProjectSyncProjectResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    project_type: str
    status: ProjectStatus
    global_config: dict[str, Any]
    updated_at: datetime


class MobileProjectSyncAssignmentResponse(BaseModel):
    id: int
    assigned_at: datetime
    updated_at: datetime


class MobileProjectSyncResponse(BaseModel):
    project: MobileProjectSyncProjectResponse
    assignment: MobileProjectSyncAssignmentResponse

    sync_hash: str

    forms: list[MobileProjectSyncFormResponse]

    files: list[MobileProjectSyncFileResponse]

    zones: list[MobileProjectSyncZoneResponse]


class MobileFormOptionResponse(BaseModel):
    id: int
    value: str
    label: str
    position: int
    option_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class MobileFormQuestionDefinitionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MobileFormQuestionVersionResponse(BaseModel):
    id: int
    version: int
    label: str
    help_text: str | None = None
    question_type: str
    base_config: dict[str, Any]
    options: list[MobileFormOptionResponse]

    model_config = ConfigDict(from_attributes=True)


class MobileFormDependencyResponse(BaseModel):
    id: int
    condition: dict[str, Any]
    actions_if_true: list[dict[str, Any]]
    actions_if_false: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class MobileFormQuestionResponse(BaseModel):
    id: int
    form_id: int
    section_id: int
    question_definition_id: int
    question_version_id: int
    position: int
    config: dict[str, Any]

    question_code: str
    question_name: str

    question_definition: MobileFormQuestionDefinitionResponse
    question_version: MobileFormQuestionVersionResponse

    dependencies: list[MobileFormDependencyResponse]

    model_config = ConfigDict(from_attributes=True)


class MobileFormSectionResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    position: int
    config: dict[str, Any]

    questions: list[MobileFormQuestionResponse]

    model_config = ConfigDict(from_attributes=True)


class MobileFormDownloadResponse(BaseModel):
    id: int
    project_id: int
    code: str
    name: str
    description: str | None = None
    form_type: str
    status: FormStatus
    global_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    sections: list[MobileFormSectionResponse]

    model_config = ConfigDict(from_attributes=True)
