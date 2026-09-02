from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DependencyAction(BaseModel):
    """
    Action exécutée lorsqu'une règle est évaluée.
    """

    type: str = Field(
        ...,
        description="Type de l'action.",
    )

    target_type: str = Field(
        ...,
        description="Type de la cible.",
    )

    target_id: int = Field(
        ...,
        description="Identifiant de la cible.",
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration spécifique à l'action.",
    )
