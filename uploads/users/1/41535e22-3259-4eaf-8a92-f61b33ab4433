from datetime import date, datetime, time
from typing import Any

from app.models.form_builder.enums import (
    DependencyConditionOperator,
    QuestionType,
)
from app.services.form_builder.dependency_operators import (
    CHOICE_TYPES,
    DATE_TYPES,
    MULTI_CHOICE_TYPES,
    NUMBER_TYPES,
    TEXT_TYPES,
    TIME_TYPES,
    get_allowed_dependency_operators,
)


def _validate_single_value(
    *,
    question_type: QuestionType,
    value: Any,
) -> None:
    """
    Vérifie qu'une valeur unique correspond au type
    de la question source.
    """

    if value is None:
        raise ValueError("Une valeur est obligatoire pour cet opérateur.")

    if question_type in NUMBER_TYPES:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("La valeur doit être numérique.")

    elif question_type in TEXT_TYPES:
        if not isinstance(value, str):
            raise ValueError("La valeur doit être une chaîne de caractères.")

    elif question_type in CHOICE_TYPES:
        if not isinstance(value, (str, int)):
            raise ValueError("La valeur doit être un identifiant d'option.")

    elif question_type in MULTI_CHOICE_TYPES:
        if not isinstance(value, (str, int)):
            raise ValueError("La valeur doit être un identifiant d'option.")

    elif question_type in DATE_TYPES:
        if not isinstance(value, (date, datetime, str)):
            raise ValueError("La valeur doit être une date valide.")

    elif question_type in TIME_TYPES:
        if not isinstance(value, (time, str)):
            raise ValueError("La valeur doit être une heure valide.")


def validate_condition_operator(
    *,
    question_type: QuestionType,
    operator: DependencyConditionOperator,
) -> None:
    allowed_operators = get_allowed_dependency_operators(
        question_type,
    )

    if operator not in allowed_operators:
        raise ValueError(
            f"L'opérateur {operator.value} "
            f"n'est pas compatible avec le type "
            f"de question {question_type.value}."
        )


def validate_comparison_value(
    *,
    question_type: QuestionType,
    operator: DependencyConditionOperator,
    value: Any,
) -> None:
    """
    Vérifie que la valeur fournie est compatible
    avec l'opérateur et le type de question.
    """
    print("type :", question_type, "opera :", operator, "value: ", value)
    # ------------------------------------------------------------
    # Opérateurs sans valeur
    # ------------------------------------------------------------

    if operator in {
        DependencyConditionOperator.IS_EMPTY,
        DependencyConditionOperator.IS_NOT_EMPTY,
        DependencyConditionOperator.IS_TRUE,
        DependencyConditionOperator.IS_FALSE,
    }:
        if value is not None:
            raise ValueError(f"L'opérateur {operator.value} " "ne doit pas recevoir de valeur.")

        return

    # ------------------------------------------------------------
    # BETWEEN / NOT_BETWEEN
    # ------------------------------------------------------------

    if operator in {
        DependencyConditionOperator.BETWEEN,
        DependencyConditionOperator.NOT_BETWEEN,
    }:
        if not isinstance(value, list):
            raise ValueError(f"L'opérateur {operator.value} " "requiert une liste de deux valeurs.")

        if len(value) != 2:
            raise ValueError(f"L'opérateur {operator.value} " "requiert exactement deux valeurs.")

        return

    # ------------------------------------------------------------
    # IN / NOT_IN
    # ------------------------------------------------------------

    if operator in {
        DependencyConditionOperator.IN,
        DependencyConditionOperator.NOT_IN,
        DependencyConditionOperator.CONTAINS_ANY,
        DependencyConditionOperator.CONTAINS_ALL,
        DependencyConditionOperator.CONTAINS_NONE,
    }:
        if not isinstance(value, list):
            raise ValueError(f"L'opérateur {operator.value} " "requiert une liste de valeurs.")

        if len(value) == 0:
            raise ValueError(f"L'opérateur {operator.value} " "requiert au moins une valeur.")

        return

    # ------------------------------------------------------------
    # Valeur simple
    # ------------------------------------------------------------

    _validate_single_value(
        question_type=question_type,
        value=value,
    )


def validate_dependency_condition(
    *,
    question_type: QuestionType,
    operator: DependencyConditionOperator,
    comparison_value: Any,
) -> None:
    """
    Valide complètement une condition.
    """

    validate_condition_operator(
        question_type=question_type,
        operator=operator,
    )

    validate_comparison_value(
        question_type=question_type,
        operator=operator,
        value=comparison_value,
    )
