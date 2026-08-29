from __future__ import annotations

from pydantic import BaseModel, Field

from .dynamic_value import DynamicValue


class DependencyCondition(BaseModel):
    """
    Condition utilisée pour déterminer si une règle doit être appliquée.
    """

    source_question_id: int = Field(
        ...,
        description="Question dont la réponse est évaluée.",
    )

    operator: str = Field(
        ...,
        description="Opérateur de comparaison.",
    )

    comparison_value: DynamicValue | None = Field(
        default=None,
        description="Valeur fixe ou dynamique utilisée pour la comparaison.",
    )
