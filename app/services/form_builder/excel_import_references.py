from __future__ import annotations

import re
from typing import Any

COLUMN_REFERENCE_PATTERN = re.compile(
    r"^col\((?P<column>.+)\)$",
    re.IGNORECASE,
)


def is_column_reference(
    value: Any,
) -> bool:
    """
    Retourne True si la valeur respecte :

        col(Nom colonne)
    """

    if not isinstance(value, str):
        return False

    return (
        COLUMN_REFERENCE_PATTERN.fullmatch(
            value.strip(),
        )
        is not None
    )


def get_column_reference(
    value: Any,
) -> str | None:
    """
    Extrait le nom de la colonne référencée.

    Exemple :

        col(Code planteur)
            -> Code planteur
    """

    if not isinstance(value, str):
        return None

    match = COLUMN_REFERENCE_PATTERN.fullmatch(
        value.strip(),
    )

    if match is None:
        return None

    column_name = match.group(
        "column",
    ).strip()

    if not column_name:
        return None

    return column_name


def collect_column_references(
    value: Any,
) -> set[str]:
    """
    Parcourt récursivement une structure JSON
    et retourne toutes les colonnes utilisées
    avec col(...).
    """

    references: set[str] = set()

    if isinstance(value, str):

        reference = get_column_reference(
            value,
        )

        if reference is not None:
            references.add(reference)

        return references

    if isinstance(value, dict):

        for item in value.values():

            references.update(
                collect_column_references(item),
            )

        return references

    if isinstance(value, list):

        for item in value:

            references.update(
                collect_column_references(item),
            )

        return references

    return references


def resolve_column_references(
    value: Any,
    *,
    row_values: dict[str, Any],
) -> Any:
    """
    Résout récursivement les références col(...).

    Exemple :

        {
            "name": "col(Nom planteur)",
            "code": "col(Code planteur)"
        }

    devient, pour une ligne donnée :

        {
            "name": "Jean",
            "code": "P001"
        }

    IMPORTANT :

    Cette fonction ne considère pas une cellule vide
    comme une valeur valide.

    Elle lève ValueError lorsqu'une référence pointe
    vers une colonne inexistante ou une cellule vide.
    """

    # ---------------------------------------------------------
    # Valeur simple
    # ---------------------------------------------------------

    if isinstance(value, str):

        column_name = get_column_reference(
            value,
        )

        # Ce n'est pas une référence.
        if column_name is None:
            return value

        # -----------------------------------------------------
        # Colonne inexistante
        # -----------------------------------------------------

        if column_name not in row_values:
            raise ValueError(f"La colonne référencée " f"'{column_name}' n'existe pas.")

        resolved_value = row_values[column_name]

        # -----------------------------------------------------
        # Cellule vide
        # -----------------------------------------------------

        if resolved_value is None:
            raise ValueError(f"La référence col({column_name}) " "pointe vers une cellule vide.")

        if isinstance(resolved_value, str) and not resolved_value.strip():
            raise ValueError(f"La référence col({column_name}) " "pointe vers une cellule vide.")

        return resolved_value

    # ---------------------------------------------------------
    # Dictionnaire
    # ---------------------------------------------------------

    if isinstance(value, dict):

        return {
            key: resolve_column_references(
                item,
                row_values=row_values,
            )
            for key, item in value.items()
        }

    # ---------------------------------------------------------
    # Liste
    # ---------------------------------------------------------

    if isinstance(value, list):

        return [
            resolve_column_references(
                item,
                row_values=row_values,
            )
            for item in value
        ]

    # ---------------------------------------------------------
    # Autres types :
    #
    # int, float, bool, None, etc.
    # ---------------------------------------------------------

    return value
