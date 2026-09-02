from __future__ import annotations

from pydantic import BaseModel, Field

from .dynamic_value import DynamicValue


class FilterOptionsConfig(BaseModel):
    """
    Configuration de l'action FILTER_OPTIONS.
    """

    filter_field: str = Field(
        ...,
        description="Champ de l'option utilisé pour filtrer.",
    )

    filter_value: DynamicValue = Field(
        ...,
        description="Valeur utilisée pour le filtrage.",
    )


class SetValueConfig(BaseModel):
    """
    Configuration de l'action SET_VALUE.
    """

    value: DynamicValue


class CopyValueConfig(BaseModel):
    """
    Configuration de l'action COPY_VALUE.
    """

    source_question_id: int = Field(
        ...,
        description="Question dont la réponse doit être copiée.",
    )


class RepeatGroupConfig(BaseModel):
    """
    Configuration de l'action REPEAT_GROUP.
    """

    count_source: DynamicValue = Field(
        ...,
        description="Source du nombre d'instances à créer.",
    )

    minimum: int = Field(
        default=0,
        ge=0,
    )

    maximum: int | None = Field(
        default=None,
        ge=1,
    )
