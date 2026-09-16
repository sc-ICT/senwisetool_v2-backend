from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    PluginFieldType,
    PluginResourceScope,
)

# ============================================================================
# FIELD
# ============================================================================


class PluginResourceFieldCreate(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
    )

    label: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    field_type: PluginFieldType

    required: bool = False

    min_length: int | None = Field(
        default=None,
        ge=0,
    )

    max_length: int | None = Field(
        default=None,
        ge=0,
    )

    min_value: float | None = None

    max_value: float | None = None

    pattern: str | None = Field(
        default=None,
        max_length=1000,
    )

    options: list[Any] = Field(
        default_factory=list,
    )

    default_value: Any | None = None

    position: int = Field(
        default=0,
        ge=0,
    )

    is_active: bool = True

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "La clé du champ est obligatoire.",
            )

        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Le libellé du champ est obligatoire.",
            )

        return value


class PluginResourceFieldUpdate(BaseModel):
    key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    label: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    field_type: PluginFieldType | None = None

    required: bool | None = None

    min_length: int | None = Field(
        default=None,
        ge=0,
    )

    max_length: int | None = Field(
        default=None,
        ge=0,
    )

    min_value: float | None = None

    max_value: float | None = None

    pattern: str | None = Field(
        default=None,
        max_length=1000,
    )

    options: list[Any] | None = None

    default_value: Any | None = None

    position: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None


class PluginResourceFieldResponse(
    PluginResourceFieldCreate,
):
    id: int
    resource_id: int

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# RESOURCE
# ============================================================================


class PluginResourceCreate(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=2,
        max_length=255,
    )

    description: str | None = None

    scope: PluginResourceScope

    allow_user_schema_override: bool = False

    position: int = Field(
        default=0,
        ge=0,
    )

    icon: str | None = Field(
        default=None,
        max_length=100,
    )

    is_active: bool = True

    fields: list[PluginResourceFieldCreate] = Field(
        default_factory=list,
    )

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "La clé de la ressource est obligatoire.",
            )

        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Le nom de la ressource est obligatoire.",
            )

        return value


class PluginResourceUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: str | None = None

    scope: PluginResourceScope | None = None

    allow_user_schema_override: bool | None = None

    position: int | None = Field(
        default=None,
        ge=0,
    )

    icon: str | None = Field(
        default=None,
        max_length=100,
    )

    is_active: bool | None = None


class PluginResourceResponse(BaseModel):
    id: int
    plugin_id: int

    key: str
    name: str
    description: str | None

    scope: PluginResourceScope

    allow_user_schema_override: bool

    schema_definition: dict[str, Any]

    position: int
    icon: str | None

    is_active: bool

    created_at: datetime
    updated_at: datetime

    fields: list[PluginResourceFieldResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


class PluginResourceListResponse(BaseModel):
    items: list[PluginResourceResponse]
    count: int


# ============================================================================
# RESOURCE RELATIONS
# ============================================================================


class PluginResourceRelationCreate(BaseModel):
    source_field_key: str = Field(
        min_length=1,
        max_length=100,
    )

    target_resource_id: int = Field(
        gt=0,
    )

    target_field_key: str = Field(
        min_length=1,
        max_length=100,
    )

    label: str | None = Field(
        default=None,
        max_length=255,
    )

    is_active: bool = True


class PluginResourceRelationResponse(BaseModel):
    id: int

    source_resource_id: int
    source_field_key: str

    target_resource_id: int
    target_field_key: str

    source_resource_name: str
    target_resource_name: str

    label: str | None

    is_active: bool

    created_at: datetime
    updated_at: datetime


class PluginResourceRelatedRecordsResponse(BaseModel):
    relation_id: int

    source_resource_id: int
    source_record_id: int

    target_resource_id: int

    direction: str

    items: list[PluginResourceRecordResponse]

    count: int


# ============================================================================
# EFFECTIVE SCHEMA
# ============================================================================


class PluginResourceEffectiveSchemaResponse(BaseModel):
    resource_id: int

    scope: PluginResourceScope

    allow_user_schema_override: bool

    is_overridden: bool

    schema_definition: dict[str, Any]

    fields: list[dict[str, Any]]


# ============================================================================
# USER SCHEMA OVERRIDE
# ============================================================================


class PluginResourceUserSchemaUpdate(BaseModel):
    fields: list[PluginResourceFieldCreate]


class PluginResourceUserSchemaResponse(BaseModel):
    id: int

    resource_id: int

    user_id: int

    schema_definition: dict[str, Any]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# RECORD
# ============================================================================


class PluginResourceRecordCreate(BaseModel):
    data: dict[str, Any]

    is_active: bool = True


class PluginResourceRecordUpdate(BaseModel):
    data: dict[str, Any] | None = None

    is_active: bool | None = None


class PluginResourceRecordResponse(BaseModel):
    id: int

    resource_id: int

    user_id: int | None

    data: dict[str, Any]

    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class PluginResourceRecordListResponse(BaseModel):
    items: list[PluginResourceRecordResponse]

    count: int


# ============================================================================
# EXCEL IMPORT
# ============================================================================


class PluginResourceImportError(BaseModel):
    row: int

    column: str | None = None

    field: str | None = None

    message: str


class PluginResourceImportResponse(BaseModel):
    resource_id: int

    imported: int

    rejected: int

    errors: list[PluginResourceImportError]


# ============================================================================
# FULL WORKBOOK IMPORT
# ============================================================================


class PluginResourceWorkbookImportResponse(BaseModel):
    plugin_id: int

    sheets: int

    resources_created: int
    resources_updated: int

    schemas_created: int
    schemas_updated: int

    relations_created: int
    relations_existing: int

    records_imported: int

    errors: list[PluginResourceImportError] = Field(
        default_factory=list,
    )
