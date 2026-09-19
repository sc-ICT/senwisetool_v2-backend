from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PluginFormTemplateCreate(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    form_type: str = Field(
        min_length=1,
        max_length=100,
    )

    position: int = 0

    required: bool = False

    min_instances: int = Field(
        default=0,
        ge=0,
    )

    max_instances: int | None = Field(
        default=None,
        ge=1,
    )

    allow_user_use: bool = True

    allow_user_customization: bool = False

    global_config: dict[str, Any] = Field(
        default_factory=dict,
    )

    definition: dict[str, Any] = Field(
        default_factory=dict,
    )

    resource_bindings: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    rules: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    metrics: list[dict[str, Any]] = Field(
        default_factory=list,
    )


class PluginFormTemplateUpdate(BaseModel):
    key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

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

    position: int | None = None

    is_active: bool | None = None

    required: bool | None = None

    min_instances: int | None = Field(
        default=None,
        ge=0,
    )

    max_instances: int | None = Field(
        default=None,
        ge=1,
    )

    allow_user_use: bool | None = None

    allow_user_customization: bool | None = None

    global_config: dict[str, Any] | None = None

    definition: dict[str, Any] | None = None

    resource_bindings: list[dict[str, Any]] | None = None

    rules: list[dict[str, Any]] | None = None

    metrics: list[dict[str, Any]] | None = None


class PluginFormTemplateResponse(BaseModel):
    id: int
    project_template_id: int
    key: str
    name: str
    description: str | None
    form_type: str
    position: int
    is_active: bool
    required: bool
    min_instances: int
    max_instances: int | None
    allow_user_use: bool
    allow_user_customization: bool
    global_config: dict[str, Any]
    definition: dict[str, Any]
    resource_bindings: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    metrics: list[dict[str, Any]]

    model_config = ConfigDict(
        from_attributes=True,
    )


class PluginFormTemplateListResponse(BaseModel):
    items: list[PluginFormTemplateResponse]
    count: int
