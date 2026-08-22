from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.form_builder.enums import (
    QuestionDefinitionStatus,
    QuestionType,
)
from app.schemas.form_builder.question_version import (
    QuestionVersionCreate,
    QuestionVersionResponse,
)


class QuestionDefinitionCreate(BaseModel):
    """
    Données nécessaires pour créer l'identité
    d'une question dans la banque.
    """

    code: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None


class QuestionDefinitionUpdate(BaseModel):
    """
    Champs modifiables d'une question de la banque.

    Le code et le type ne sont pas modifiés directement
    sur une question existante.

    Une évolution structurelle passera par une nouvelle version.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    status: QuestionDefinitionStatus | None = None


class QuestionDefinitionResponse(BaseModel):
    """
    Représentation d'une question de la banque
    renvoyée par l'API.
    """

    id: int
    code: str
    name: str
    description: str | None
    status: QuestionDefinitionStatus
    created_by: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class QuestionDefinitionListResponse(BaseModel):
    """
    Réponse de la liste de questions.
    """

    items: list[QuestionDefinitionListItemResponse]
    count: int


class QuestionCreateRequest(BaseModel):
    """
    Payload complet utilisé pour créer une question
    et sa première version en une seule opération.
    """

    definition: QuestionDefinitionCreate
    version: QuestionVersionCreate


class QuestionDefinitionDetailResponse(BaseModel):
    """
    Détail complet d'une question de la banque.
    """

    id: int
    code: str
    name: str
    description: str | None
    status: QuestionDefinitionStatus
    created_by: int
    versions: list[QuestionVersionResponse]

    model_config = ConfigDict(
        from_attributes=True,
    )


class QuestionVersionListResponse(BaseModel):
    """
    Liste des versions d'une question.
    """

    items: list[QuestionVersionResponse]
    count: int


class QuestionDuplicateRequest(BaseModel):
    """
    Données nécessaires pour créer une nouvelle question
    indépendante à partir d'une question existante.
    """

    code: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None


class QuestionDefinitionListItemResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    status: QuestionDefinitionStatus
    created_by: int
    current_version: int | None
    question_type: QuestionType | None

    model_config = ConfigDict(
        from_attributes=True,
    )
