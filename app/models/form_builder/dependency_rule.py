from __future__ import annotations

from pydantic import BaseModel, Field

from .dependency_action import DependencyAction
from .dependency_condition import DependencyCondition


class DependencyConditionGroup(BaseModel):
    """
    Groupe logique permettant de combiner des conditions
    et d'autres groupes.
    """

    operator: str = "AND"

    conditions: list[DependencyCondition] = Field(
        default_factory=list,
    )

    groups: list["DependencyConditionGroup"] = Field(
        default_factory=list,
    )


class DependencyRule(BaseModel):
    """
    Règle complète de comportement dynamique.
    """

    condition: DependencyConditionGroup

    actions_if_true: list[DependencyAction] = Field(
        default_factory=list,
    )

    actions_if_false: list[DependencyAction] = Field(
        default_factory=list,
    )


DependencyConditionGroup.model_rebuild()
