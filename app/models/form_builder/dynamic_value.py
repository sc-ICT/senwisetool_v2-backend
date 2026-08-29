from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DynamicValue(BaseModel):
    """
    Représente une valeur pouvant être fixe ou provenir
    dynamiquement d'une autre question.
    """

    source_type: str = Field(..., description="Type de source de la valeur.")

    value: Any = Field(default=None, description="Valeur fixe lorsque source_type = CONSTANT.")

    question_id: int | None = Field(
        default=None, description="Question source lorsque source_type = QUESTION."
    )
