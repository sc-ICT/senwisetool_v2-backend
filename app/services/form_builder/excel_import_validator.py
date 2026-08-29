from typing import Any

from app.services.form_builder.excel_import_parser import ParsedSheet
from app.services.form_builder.excel_import_references import (
    get_column_reference,
)

# ---------------------------------------------------------------------------
# Paramètres reconnus au niveau de l'import
# ---------------------------------------------------------------------------

QUESTION_TYPES = {
    "SHORT_TEXT",
    "LONG_TEXT",
    "INTEGER",
    "DECIMAL",
    "PERCENTAGE",
    "CURRENCY",
    "DATE",
    "DATETIME",
    "TIME",
    "EMAIL",
    "PHONE",
    "URL",
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "DROPDOWN",
    "AUTOCOMPLETE",
    "LIKERT_SCALE",
    "BOOLEAN",
    "FILE",
    "IMAGE",
    "SIGNATURE",
}

TARGET_TYPES = {
    "QUESTION",
    "SECTION",
}

ACTION_TYPES = {
    "SHOW",
    "HIDE",
    "ENABLE",
    "DISABLE",
    "REQUIRE",
    "OPTIONAL",
    "READONLY",
    "EDITABLE",
    "SET_VALUE",
    "COPY_VALUE",
    "FILTER_OPTIONS",
    "CLEAR_VALUE",
    "REPEAT_SECTION",
}

CONDITION_OPERATORS = {
    "EQUALS",
    "NOT_EQUALS",
    "IN",
    "NOT_IN",
    "GREATER_THAN",
    "GREATER_THAN_OR_EQUALS",
    "LESS_THAN",
    "LESS_THAN_OR_EQUALS",
    "CONTAINS",
    "NOT_CONTAINS",
    "IS_EMPTY",
    "IS_NOT_EMPTY",
}

LOGICAL_OPERATORS = {
    "AND",
    "OR",
}

COMPARISON_SOURCE_TYPES = {
    "CONSTANT",
    "QUESTION",
}


# ---------------------------------------------------------------------------
# Erreurs
# ---------------------------------------------------------------------------


class ExcelImportValidationError(ValueError):
    """
    Erreur de validation du fichier Excel.

    Aucune écriture en base ne doit être effectuée lorsqu'une de ces
    erreurs est levée.
    """

    def __init__(
        self,
        message: str,
        *,
        sheet: str | None = None,
        row: int | None = None,
        column: str | None = None,
    ) -> None:
        self.sheet = sheet
        self.row = row
        self.column = column

        location = ""

        if sheet:
            location += f"[Feuille: {sheet}]"

        if row is not None:
            location += f"[Ligne: {row}]"

        if column:
            location += f"[Colonne: {column}]"

        if location:
            message = f"{location} {message}"

        super().__init__(message)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_string(
    value: Any,
    *,
    field: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExcelImportValidationError(
            f"Le paramètre '{field}' est obligatoire " "et doit être une chaîne de caractères."
        )

    return value.strip()


def _require_positive_int(
    value: Any,
    *,
    field: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExcelImportValidationError(f"Le paramètre '{field}' doit être un entier positif.")

    return value


def _validate_column_references(
    value: Any,
    *,
    sheet: str,
    row: int | None,
    column: str | None,
    available_columns: set[str],
) -> None:
    """
    Vérifie récursivement toutes les références col(...).
    """

    if isinstance(value, str):
        reference = get_column_reference(value)

        if reference is None:
            return

        if reference not in available_columns:
            raise ExcelImportValidationError(
                f"La référence '{value}' pointe vers une colonne "
                "qui n'existe pas dans cette feuille.",
                sheet=sheet,
                row=row,
                column=column,
            )

        return

    if isinstance(value, dict):
        for item in value.values():
            _validate_column_references(
                item,
                sheet=sheet,
                row=row,
                column=column,
                available_columns=available_columns,
            )

        return

    if isinstance(value, list):
        for item in value:
            _validate_column_references(
                item,
                sheet=sheet,
                row=row,
                column=column,
                available_columns=available_columns,
            )


# ---------------------------------------------------------------------------
# Validation d'une question
# ---------------------------------------------------------------------------


def _validate_question_parameters(
    parameters: dict[str, Any],
    *,
    sheet: str,
    column: str,
    available_columns: set[str],
) -> None:
    question_type = parameters.get("question_type")

    if question_type is None:
        question_type = parameters.get("type")

    if not isinstance(question_type, str):
        raise ExcelImportValidationError(
            "Une colonne de question doit obligatoirement définir " "'question_type'.",
            sheet=sheet,
            column=column,
        )

    question_type = question_type.strip().upper()

    if question_type not in QUESTION_TYPES:
        raise ExcelImportValidationError(
            f"Type de question inconnu : '{question_type}'.",
            sheet=sheet,
            column=column,
        )

    # -----------------------------------------------------------------------
    # Tous les paramètres sont parcourus pour détecter les références
    # col(...), quel que soit leur emplacement.
    # -----------------------------------------------------------------------

    _validate_column_references(
        parameters,
        sheet=sheet,
        row=2,
        column=column,
        available_columns=available_columns,
    )

    # -----------------------------------------------------------------------
    # Groupe
    # -----------------------------------------------------------------------

    group = parameters.get("group")

    if group is not None and not isinstance(group, str):
        raise ExcelImportValidationError(
            "'group' doit être une chaîne de caractères.",
            sheet=sheet,
            column=column,
        )

    # -----------------------------------------------------------------------
    # Section
    # -----------------------------------------------------------------------

    section = parameters.get("section")

    if section is not None and not isinstance(section, str):
        raise ExcelImportValidationError(
            "'section' doit être une chaîne de caractères.",
            sheet=sheet,
            column=column,
        )

    # -----------------------------------------------------------------------
    # Position
    # -----------------------------------------------------------------------

    if "position" in parameters:
        position = parameters["position"]

        if not isinstance(position, int) or isinstance(position, bool) or position < 0:
            raise ExcelImportValidationError(
                "'position' doit être un entier supérieur ou égal à zéro.",
                sheet=sheet,
                column=column,
            )

    # -----------------------------------------------------------------------
    # Options
    # -----------------------------------------------------------------------

    if question_type in {
        "SINGLE_CHOICE",
        "MULTIPLE_CHOICE",
        "DROPDOWN",
        "AUTOCOMPLETE",
        "LIKERT_SCALE",
    }:
        options = parameters.get("options")

        if options is not None:
            if not isinstance(options, list):
                raise ExcelImportValidationError(
                    "'options' doit être une liste.",
                    sheet=sheet,
                    column=column,
                )

            for index, option in enumerate(options):
                if not isinstance(option, dict):
                    raise ExcelImportValidationError(
                        f"L'option {index + 1} doit être un objet JSON.",
                        sheet=sheet,
                        column=column,
                    )

                if "label" not in option:
                    raise ExcelImportValidationError(
                        f"L'option {index + 1} doit contenir 'label'.",
                        sheet=sheet,
                        column=column,
                    )

                if "value" not in option:
                    raise ExcelImportValidationError(
                        f"L'option {index + 1} doit contenir 'value'.",
                        sheet=sheet,
                        column=column,
                    )

    # -----------------------------------------------------------------------
    # Dépendances
    # -----------------------------------------------------------------------

    dependency = parameters.get("dependency")

    if dependency is not None:
        _validate_dependency(
            dependency,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )

    dependencies = parameters.get("dependencies")

    if dependencies is not None:
        if not isinstance(dependencies, list):
            raise ExcelImportValidationError(
                "'dependencies' doit être une liste.",
                sheet=sheet,
                column=column,
            )

        for dependency_item in dependencies:
            _validate_dependency(
                dependency_item,
                sheet=sheet,
                column=column,
                available_columns=available_columns,
            )


# ---------------------------------------------------------------------------
# Validation d'une dépendance
# ---------------------------------------------------------------------------


def _validate_dependency(
    dependency: Any,
    *,
    sheet: str,
    column: str,
    available_columns: set[str],
) -> None:
    if not isinstance(dependency, dict):
        raise ExcelImportValidationError(
            "Une dépendance doit être un objet JSON.",
            sheet=sheet,
            column=column,
        )

    condition = dependency.get("condition")

    if not isinstance(condition, dict):
        raise ExcelImportValidationError(
            "Une dépendance doit contenir un objet 'condition'.",
            sheet=sheet,
            column=column,
        )

    operator = condition.get("operator")

    if operator not in LOGICAL_OPERATORS:
        raise ExcelImportValidationError(
            "'condition.operator' doit être 'AND' ou 'OR'.",
            sheet=sheet,
            column=column,
        )

    conditions = condition.get("conditions")

    if not isinstance(conditions, list) or not conditions:
        raise ExcelImportValidationError(
            "'condition.conditions' doit contenir au moins " "une condition.",
            sheet=sheet,
            column=column,
        )

    for item in conditions:
        _validate_single_condition(
            item,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )

    groups = condition.get("groups", [])

    if not isinstance(groups, list):
        raise ExcelImportValidationError(
            "'condition.groups' doit être une liste.",
            sheet=sheet,
            column=column,
        )

    for group in groups:
        _validate_dependency_condition_group(
            group,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )

    actions_if_true = dependency.get("actions_if_true", [])

    if not isinstance(actions_if_true, list):
        raise ExcelImportValidationError(
            "'actions_if_true' doit être une liste.",
            sheet=sheet,
            column=column,
        )

    actions_if_false = dependency.get("actions_if_false", [])

    if not isinstance(actions_if_false, list):
        raise ExcelImportValidationError(
            "'actions_if_false' doit être une liste.",
            sheet=sheet,
            column=column,
        )

    if not actions_if_true and not actions_if_false:
        raise ExcelImportValidationError(
            "Une dépendance doit contenir au moins une action.",
            sheet=sheet,
            column=column,
        )

    for action in actions_if_true:
        _validate_action(
            action,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )

    for action in actions_if_false:
        _validate_action(
            action,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )


def _validate_dependency_condition_group(
    group: Any,
    *,
    sheet: str,
    column: str,
    available_columns: set[str],
) -> None:
    if not isinstance(group, dict):
        raise ExcelImportValidationError(
            "Chaque groupe de conditions doit être un objet JSON.",
            sheet=sheet,
            column=column,
        )

    operator = group.get("operator")

    if operator not in LOGICAL_OPERATORS:
        raise ExcelImportValidationError(
            "Le groupe de conditions doit utiliser 'AND' ou 'OR'.",
            sheet=sheet,
            column=column,
        )

    conditions = group.get("conditions", [])

    if not isinstance(conditions, list):
        raise ExcelImportValidationError(
            "'conditions' doit être une liste.",
            sheet=sheet,
            column=column,
        )

    for item in conditions:
        _validate_single_condition(
            item,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )

    nested_groups = group.get("groups", [])

    if not isinstance(nested_groups, list):
        raise ExcelImportValidationError(
            "'groups' doit être une liste.",
            sheet=sheet,
            column=column,
        )

    for nested_group in nested_groups:
        _validate_dependency_condition_group(
            nested_group,
            sheet=sheet,
            column=column,
            available_columns=available_columns,
        )


def _validate_single_condition(
    condition: Any,
    *,
    sheet: str,
    column: str,
    available_columns: set[str],
) -> None:
    if not isinstance(condition, dict):
        raise ExcelImportValidationError(
            "Chaque condition doit être un objet JSON.",
            sheet=sheet,
            column=column,
        )

    source_question_id = condition.get("source_question_id")

    source_question = condition.get("source_question")

    if source_question_id is None and source_question is None:
        raise ExcelImportValidationError(
            "Une condition doit définir 'source_question_id' " "ou 'source_question'.",
            sheet=sheet,
            column=column,
        )

    if source_question_id is not None:
        _validate_question_reference(
            source_question_id,
            field="source_question_id",
            sheet=sheet,
            column=column,
        )

    if source_question is not None:
        if not isinstance(source_question, str):
            raise ExcelImportValidationError(
                "'source_question' doit être une chaîne.",
                sheet=sheet,
                column=column,
            )

    operator = condition.get("operator")

    if operator not in CONDITION_OPERATORS:
        raise ExcelImportValidationError(
            f"Opérateur de condition inconnu : '{operator}'.",
            sheet=sheet,
            column=column,
        )

    comparison = condition.get("comparison_value")

    if operator not in {"IS_EMPTY", "IS_NOT_EMPTY"}:
        if not isinstance(comparison, dict):
            raise ExcelImportValidationError(
                "Cette condition doit définir 'comparison_value'.",
                sheet=sheet,
                column=column,
            )

        source_type = comparison.get("source_type")

        if source_type not in COMPARISON_SOURCE_TYPES:
            raise ExcelImportValidationError(
                "'comparison_value.source_type' doit être " "'CONSTANT' ou 'QUESTION'.",
                sheet=sheet,
                column=column,
            )

        if source_type == "CONSTANT":
            if "value" not in comparison and "value_column" not in comparison:
                raise ExcelImportValidationError(
                    "Une comparaison CONSTANT doit définir 'value' " "ou 'value_column'.",
                    sheet=sheet,
                    column=column,
                )

        if source_type == "QUESTION":
            question_id = comparison.get("question_id")
            question = comparison.get("question")

            if question_id is None and question is None:
                raise ExcelImportValidationError(
                    "Une comparaison QUESTION doit définir " "'question_id' ou 'question'.",
                    sheet=sheet,
                    column=column,
                )

            if question_id is not None:
                _validate_question_reference(
                    question_id,
                    field="comparison_value.question_id",
                    sheet=sheet,
                    column=column,
                )

            if question is not None and not isinstance(question, str):
                raise ExcelImportValidationError(
                    "'comparison_value.question' doit être une chaîne.",
                    sheet=sheet,
                    column=column,
                )

    _validate_column_references(
        condition,
        sheet=sheet,
        row=2,
        column=column,
        available_columns=available_columns,
    )


# ---------------------------------------------------------------------------
# Validation d'une action
# ---------------------------------------------------------------------------


def _validate_action(
    action: Any,
    *,
    sheet: str,
    column: str,
    available_columns: set[str],
) -> None:
    if not isinstance(action, dict):
        raise ExcelImportValidationError(
            "Chaque action doit être un objet JSON.",
            sheet=sheet,
            column=column,
        )

    action_type = action.get("type")

    if action_type not in ACTION_TYPES:
        raise ExcelImportValidationError(
            f"Type d'action inconnu : '{action_type}'.",
            sheet=sheet,
            column=column,
        )

    target_type = action.get("target_type")

    if target_type not in TARGET_TYPES:
        raise ExcelImportValidationError(
            "'target_type' doit être 'QUESTION' ou 'SECTION'.",
            sheet=sheet,
            column=column,
        )

    target_id = action.get("target_id")

    target = action.get("target")

    if target_id is None and target is None:
        raise ExcelImportValidationError(
            "Une action doit définir 'target_id' ou 'target'.",
            sheet=sheet,
            column=column,
        )

    if target_id is not None:
        _validate_question_reference(
            target_id,
            field="target_id",
            sheet=sheet,
            column=column,
        )

    if target is not None and not isinstance(target, str):
        raise ExcelImportValidationError(
            "'target' doit être une chaîne.",
            sheet=sheet,
            column=column,
        )

    config = action.get("config", {})

    if not isinstance(config, dict):
        raise ExcelImportValidationError(
            "'config' doit être un objet JSON.",
            sheet=sheet,
            column=column,
        )

    if action_type == "COPY_VALUE":
        if "source_question_id" not in config and "source_question" not in config:
            raise ExcelImportValidationError(
                "COPY_VALUE nécessite 'source_question_id' " "ou 'source_question'.",
                sheet=sheet,
                column=column,
            )

    if action_type == "SET_VALUE":
        if "value" not in config and "value_column" not in config:
            raise ExcelImportValidationError(
                "SET_VALUE nécessite 'value' ou 'value_column'.",
                sheet=sheet,
                column=column,
            )

    if action_type == "FILTER_OPTIONS":
        if not config.get("filter_field"):
            raise ExcelImportValidationError(
                "FILTER_OPTIONS nécessite 'filter_field'.",
                sheet=sheet,
                column=column,
            )

        if "filter_value" not in config and "filter_value_column" not in config:
            raise ExcelImportValidationError(
                "FILTER_OPTIONS nécessite 'filter_value' " "ou 'filter_value_column'.",
                sheet=sheet,
                column=column,
            )

    if action_type == "REPEAT_SECTION":
        if target_type != "SECTION":
            raise ExcelImportValidationError(
                "REPEAT_SECTION doit cibler une section.",
                sheet=sheet,
                column=column,
            )

        if "count_source" not in config:
            raise ExcelImportValidationError(
                "REPEAT_SECTION nécessite 'count_source'.",
                sheet=sheet,
                column=column,
            )

    _validate_column_references(
        action,
        sheet=sheet,
        row=2,
        column=column,
        available_columns=available_columns,
    )


def _validate_question_reference(
    value: Any,
    *,
    field: str,
    sheet: str,
    column: str,
) -> None:
    if isinstance(value, str):
        # Une référence textuelle sera résolue ultérieurement
        # par le moteur d'import.
        if not value.strip():
            raise ExcelImportValidationError(
                f"'{field}' ne peut pas être vide.",
                sheet=sheet,
                column=column,
            )

        return

    if isinstance(value, int) and not isinstance(value, bool):
        if value > 0:
            return

    raise ExcelImportValidationError(
        f"'{field}' doit être un identifiant positif " "ou une référence textuelle.",
        sheet=sheet,
        column=column,
    )


# ---------------------------------------------------------------------------
# Validation globale du workbook
# ---------------------------------------------------------------------------


def validate_parsed_sheets(
    sheets: list[ParsedSheet],
) -> None:
    if not sheets:
        raise ExcelImportValidationError("Le fichier Excel ne contient aucune feuille exploitable.")

    total_question_columns = 0

    for parsed_sheet in sheets:
        if not parsed_sheet.columns:
            raise ExcelImportValidationError(
                "La feuille ne contient aucune colonne.",
                sheet=parsed_sheet.name,
            )

        available_columns = {column.name for column in parsed_sheet.columns}

        question_columns = parsed_sheet.question_columns

        if not question_columns:
            raise ExcelImportValidationError(
                "La feuille doit contenir au moins une colonne "
                "de question. Une colonne de question est une colonne "
                "dont la deuxième ligne contient un objet JSON.",
                sheet=parsed_sheet.name,
            )

        total_question_columns += len(question_columns)

        for question_column in question_columns:
            if question_column.parameters is None:
                continue

            _validate_question_parameters(
                question_column.parameters,
                sheet=parsed_sheet.name,
                column=question_column.name,
                available_columns=available_columns,
            )

    if total_question_columns == 0:
        raise ExcelImportValidationError("Aucune question n'a été détectée dans le fichier.")
