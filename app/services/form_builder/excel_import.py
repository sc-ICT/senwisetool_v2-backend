from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExcelImportQuestionVersion(BaseModel):
    """
    Paramètres permettant de créer/configurer la version
    d'une question.
    """

    model_config = ConfigDict(extra="allow")

    question_type: str

    label: str | None = None

    description: str | None = None

    help_text: str | None = None

    placeholder: str | None = None

    required: bool | None = None

    base_config: dict[str, Any] = Field(
        default_factory=dict,
    )

    options: list[dict[str, Any]] = Field(
        default_factory=list,
    )


class ExcelImportQuestionFormConfig(BaseModel):
    """
    Paramètres liés à l'ajout de la question au formulaire.
    """

    model_config = ConfigDict(extra="allow")

    position: int | None = None

    is_required: bool | None = None

    is_visible: bool | None = None

    config: dict[str, Any] = Field(
        default_factory=dict,
    )


class ExcelImportQuestion(BaseModel):
    """
    Configuration complète d'une question importée.
    """

    model_config = ConfigDict(extra="allow")

    code: str

    name: str | None = None

    description: str | None = None

    group: str | None = None

    version: ExcelImportQuestionVersion

    form: ExcelImportQuestionFormConfig = Field(
        default_factory=ExcelImportQuestionFormConfig,
    )


class ExcelImportConditionComparison(BaseModel):
    """
    Valeur utilisée pour comparer une question.
    """

    model_config = ConfigDict(extra="allow")

    source_type: Literal["CONSTANT", "QUESTION"]

    value: Any | None = None

    question_code: str | None = None


class ExcelImportCondition(BaseModel):
    """
    Une condition de dépendance.
    """

    model_config = ConfigDict(extra="allow")

    source_question_code: str

    operator: str

    comparison_value: ExcelImportConditionComparison | None = None


class ExcelImportConditionGroup(BaseModel):
    """
    Groupe de conditions.
    """

    model_config = ConfigDict(extra="allow")

    operator: Literal["AND", "OR"] = "AND"

    conditions: list[ExcelImportCondition] = Field(
        default_factory=list,
    )

    groups: list["ExcelImportConditionGroup"] = Field(
        default_factory=list,
    )


class ExcelImportAction(BaseModel):
    """
    Action de dépendance.

    target_question_code permet de cibler une question
    du même fichier sans connaître son ID en base.

    target_type peut également être SECTION.
    """

    model_config = ConfigDict(extra="allow")

    type: str

    target_type: Literal["QUESTION", "SECTION"] = "QUESTION"

    target_question_code: str | None = None

    target_section_name: str | None = None

    config: dict[str, Any] = Field(
        default_factory=dict,
    )


class ExcelImportDependency(BaseModel):
    """
    Configuration complète d'une dépendance.
    """

    model_config = ConfigDict(extra="allow")

    condition: ExcelImportConditionGroup

    actions_if_true: list[ExcelImportAction] = Field(
        default_factory=list,
    )

    actions_if_false: list[ExcelImportAction] = Field(
        default_factory=list,
    )


class ExcelImportQuestionParameters(BaseModel):
    """
    Template racine placé dans la deuxième ligne
    de chaque colonne-question.

    Il regroupe :

        - création de la question
        - configuration de sa version
        - ajout au formulaire
        - groupe
        - dépendances
    """

    model_config = ConfigDict(extra="allow")

    question: ExcelImportQuestion

    dependency: ExcelImportDependency | None = None
