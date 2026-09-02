from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.form_builder.enums import QuestionType


class QuestionOptionCreate(BaseModel):
    """
    Données nécessaires pour créer une option
    dans une version de question.
    """

    value: str = Field(
        min_length=1,
        max_length=255,
    )

    label: str = Field(
        min_length=1,
        max_length=500,
    )

    position: int = Field(
        ge=0,
    )

    option_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class QuestionOptionUpdate(BaseModel):
    """
    Champs modifiables d'une option.
    """

    value: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    label: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    position: int | None = Field(
        default=None,
        ge=0,
    )

    option_metadata: dict[str, Any] | None = None


class QuestionOptionResponse(BaseModel):
    """
    Option renvoyée par l'API.
    """

    id: int
    value: str
    label: str
    position: int
    option_metadata: dict[str, Any]

    model_config = ConfigDict(
        from_attributes=True,
    )


class QuestionVersionCreate(BaseModel):
    """
    Données nécessaires pour créer une nouvelle
    version d'une question.

    Le numéro de version est généré par le backend.
    question_definition_id est également déterminé
    par le contexte de la requête.
    """

    label: str = Field(
        min_length=1,
        max_length=500,
    )

    help_text: str | None = None

    question_type: QuestionType

    base_config: dict[str, Any] = Field(
        default_factory=dict,
    )

    options: list[QuestionOptionCreate] = Field(
        default_factory=list,
    )


class QuestionVersionUpdate(BaseModel):
    """
    Données modifiables d'une version de question.

    Une version publiée devra devenir immuable
    au niveau du service métier.
    """

    label: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    help_text: str | None = None

    question_type: QuestionType | None = None

    base_config: dict[str, Any] | None = None

    options: list[QuestionOptionCreate] | None = None


class QuestionVersionResponse(BaseModel):
    """
    Version complète d'une question renvoyée par l'API.
    """

    id: int
    question_definition_id: int
    version: int
    label: str
    help_text: str | None
    question_type: QuestionType
    base_config: dict[str, Any]
    created_by: int
    options: list[QuestionOptionResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


class QuestionVersionListResponse(BaseModel):
    """
    Liste des versions d'une question.
    """

    items: list[QuestionVersionResponse]
    count: int
