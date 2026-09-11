from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PluginStatus, PluginVersionStatus

# ============================================================================
# CREATE
# ============================================================================


class PluginCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=255,
    )

    description: str = Field(
        min_length=1,
    )

    short_description: str | None = Field(
        default=None,
        max_length=500,
    )

    icon_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    banner_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    category: str | None = Field(
        default=None,
        max_length=100,
    )

    tags: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    parameters: dict = Field(
        default_factory=dict,
    )

    metadata_config: dict = Field(
        default_factory=dict,
    )

    initial_version: str = Field(
        default="1.0.0",
        min_length=1,
        max_length=50,
    )

    release_notes: str | None = None

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Cette valeur est obligatoire.")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "La description du plugin est obligatoire.",
            )

        return value

    @field_validator("short_description", "category")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("initial_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "La version initiale est obligatoire.",
            )

        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []

        for tag in value:
            tag = tag.strip()

            if not tag:
                continue

            if tag not in normalized:
                normalized.append(tag)

        return normalized


# ============================================================================
# UPDATE
# ============================================================================


class PluginUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
    )

    short_description: str | None = Field(
        default=None,
        max_length=500,
    )

    icon_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    banner_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    category: str | None = Field(
        default=None,
        max_length=100,
    )

    tags: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    parameters: dict | None = None

    metadata_config: dict | None = None

    @field_validator("name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Cette valeur est obligatoire.")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "La description du plugin ne peut pas être vide.",
            )

        return value

    @field_validator("short_description", "category")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None

        normalized: list[str] = []

        for tag in value:
            tag = tag.strip()

            if not tag:
                continue

            if tag not in normalized:
                normalized.append(tag)

        return normalized


# ============================================================================
# VERSION RESPONSE
# ============================================================================


class PluginVersionResponse(BaseModel):
    id: int
    plugin_id: int

    version: str
    status: PluginVersionStatus

    definition: dict
    definition_hash: str | None

    release_notes: str | None

    published_at: datetime | None
    deprecated_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# PLUGIN RESPONSE
# ============================================================================


class PluginResponse(BaseModel):
    id: int
    code: str
    name: str
    slug: str

    description: str
    short_description: str | None

    icon_url: str | None
    banner_url: str | None

    category: str | None
    tags: list

    parameters: dict
    metadata_config: dict

    status: PluginStatus
    is_public: bool

    created_by: int

    published_at: datetime | None
    unpublished_at: datetime | None

    created_at: datetime
    updated_at: datetime

    versions: list[PluginVersionResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# LIST RESPONSE
# ============================================================================


class PluginListResponse(BaseModel):
    items: list[PluginResponse]
    count: int
