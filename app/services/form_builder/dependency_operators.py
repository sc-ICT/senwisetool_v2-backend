from app.models.form_builder.enums import (
    DependencyConditionOperator,
    QuestionType,
)

TEXT_TYPES = {
    QuestionType.TEXT,
    QuestionType.LONG_TEXT,
    QuestionType.EMAIL,
    QuestionType.PHONE,
    QuestionType.URL,
    QuestionType.ADDRESS,
}


NUMBER_TYPES = {
    QuestionType.INTEGER,
    QuestionType.DECIMAL,
    QuestionType.PERCENTAGE,
    QuestionType.CURRENCY,
    QuestionType.RATING,
}


CHOICE_TYPES = {
    QuestionType.SINGLE_CHOICE,
    QuestionType.DROPDOWN,
    QuestionType.AUTOCOMPLETE,
    QuestionType.LIKERT_SCALE,
    QuestionType.ENTITY_SELECT,
    QuestionType.ENTITY_SEARCH,
}


MULTI_CHOICE_TYPES = {
    QuestionType.MULTIPLE_CHOICE,
}


DATE_TYPES = {
    QuestionType.DATE,
    QuestionType.DATETIME,
}


TIME_TYPES = {
    QuestionType.TIME,
}


BOOLEAN_TYPES = {
    QuestionType.CONSENT,
}


def get_allowed_dependency_operators(
    question_type: QuestionType,
) -> set[DependencyConditionOperator]:

    if question_type in TEXT_TYPES:
        return {
            DependencyConditionOperator.EQUALS,
            DependencyConditionOperator.NOT_EQUALS,
            DependencyConditionOperator.CONTAINS,
            DependencyConditionOperator.NOT_CONTAINS,
            DependencyConditionOperator.STARTS_WITH,
            DependencyConditionOperator.NOT_STARTS_WITH,
            DependencyConditionOperator.ENDS_WITH,
            DependencyConditionOperator.NOT_ENDS_WITH,
            DependencyConditionOperator.MATCHES_REGEX,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    if question_type in NUMBER_TYPES:
        return {
            DependencyConditionOperator.EQUALS,
            DependencyConditionOperator.NOT_EQUALS,
            DependencyConditionOperator.GREATER_THAN,
            DependencyConditionOperator.GREATER_THAN_OR_EQUALS,
            DependencyConditionOperator.LESS_THAN,
            DependencyConditionOperator.LESS_THAN_OR_EQUALS,
            DependencyConditionOperator.BETWEEN,
            DependencyConditionOperator.NOT_BETWEEN,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    if question_type in CHOICE_TYPES:
        return {
            DependencyConditionOperator.EQUALS,
            DependencyConditionOperator.NOT_EQUALS,
            DependencyConditionOperator.IN,
            DependencyConditionOperator.NOT_IN,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    if question_type in MULTI_CHOICE_TYPES:
        return {
            DependencyConditionOperator.CONTAINS_ANY,
            DependencyConditionOperator.CONTAINS_ALL,
            DependencyConditionOperator.CONTAINS_NONE,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    if question_type in DATE_TYPES:
        return {
            DependencyConditionOperator.EQUALS,
            DependencyConditionOperator.NOT_EQUALS,
            DependencyConditionOperator.GREATER_THAN,
            DependencyConditionOperator.GREATER_THAN_OR_EQUALS,
            DependencyConditionOperator.LESS_THAN,
            DependencyConditionOperator.LESS_THAN_OR_EQUALS,
            DependencyConditionOperator.BETWEEN,
            DependencyConditionOperator.NOT_BETWEEN,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    if question_type in TIME_TYPES:
        return {
            DependencyConditionOperator.EQUALS,
            DependencyConditionOperator.NOT_EQUALS,
            DependencyConditionOperator.GREATER_THAN,
            DependencyConditionOperator.GREATER_THAN_OR_EQUALS,
            DependencyConditionOperator.LESS_THAN,
            DependencyConditionOperator.LESS_THAN_OR_EQUALS,
            DependencyConditionOperator.BETWEEN,
            DependencyConditionOperator.NOT_BETWEEN,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    if question_type in BOOLEAN_TYPES:
        return {
            DependencyConditionOperator.IS_TRUE,
            DependencyConditionOperator.IS_FALSE,
            DependencyConditionOperator.IS_EMPTY,
            DependencyConditionOperator.IS_NOT_EMPTY,
        }

    return {
        DependencyConditionOperator.IS_EMPTY,
        DependencyConditionOperator.IS_NOT_EMPTY,
    }
