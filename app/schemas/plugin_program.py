from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ScheduleType = Literal[
    "ONE_TIME",
    "RECURRING",
    "CUSTOM",
]

ExecutionMode = Literal[
    "MANUAL",
    "AUTOMATIC",
]

ScheduleUnit = Literal[
    "DAY",
    "WEEK",
    "MONTH",
    "YEAR",
]

ProgramScope = Literal[
    "GLOBAL",
    "USER",
]

ProgramStatus = Literal[
    "DRAFT",
    "ACTIVE",
    "PAUSED",
    "COMPLETED",
    "ARCHIVED",
]


class ProgramCustomOccurrence(BaseModel):
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_dates(self) -> "ProgramCustomOccurrence":
        if self.end_at <= self.start_at:
            raise ValueError(
                "La date de fin d'une occurrence doit être postérieure " "à sa date de début."
            )

        return self


class ProgramSchedule(BaseModel):
    """
    Configuration temporelle du programme.

    ONE_TIME:
        start_at + end_at

    RECURRING:
        start_at
        optional end_at = fin globale de la récurrence
        recurrence_unit
        recurrence_interval
        occurrence_duration
        occurrence_duration_unit
        gap_duration
        gap_duration_unit

    CUSTOM:
        custom_occurrences
    """

    type: ScheduleType = "ONE_TIME"

    execution_mode: ExecutionMode = "MANUAL"

    timezone: str = "UTC"

    start_at: datetime | None = None

    end_at: datetime | None = None

    recurrence_unit: ScheduleUnit | None = None

    recurrence_interval: int | None = Field(
        default=None,
        ge=1,
    )

    occurrence_duration: int | None = Field(
        default=None,
        ge=1,
    )

    occurrence_duration_unit: ScheduleUnit | None = None

    gap_duration: int = Field(
        default=0,
        ge=0,
    )

    gap_duration_unit: ScheduleUnit = "DAY"

    custom_occurrences: list[ProgramCustomOccurrence] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_schedule(self) -> "ProgramSchedule":
        if self.type == "ONE_TIME":
            if self.start_at is None:
                raise ValueError("Une programmation unique doit avoir une date de début.")

            if self.end_at is None:
                raise ValueError("Une programmation unique doit avoir une date de fin.")

            if self.end_at <= self.start_at:
                raise ValueError("La date de fin doit être postérieure à la date de début.")

        elif self.type == "RECURRING":
            if self.start_at is None:
                raise ValueError("Une récurrence doit avoir une date de début.")

            if self.recurrence_unit is None:
                raise ValueError("L'unité de récurrence est obligatoire.")

            if self.recurrence_interval is None:
                raise ValueError("L'intervalle de récurrence est obligatoire.")

            if self.occurrence_duration is None:
                raise ValueError("La durée d'une occurrence est obligatoire.")

            if self.occurrence_duration_unit is None:
                raise ValueError("L'unité de durée d'une occurrence est obligatoire.")

            if self.end_at is not None and self.end_at <= self.start_at:
                raise ValueError(
                    "La fin globale de la récurrence doit être " "postérieure au début."
                )

        elif self.type == "CUSTOM":
            if not self.custom_occurrences:
                raise ValueError(
                    "Une programmation personnalisée doit contenir " "au moins une occurrence."
                )

            ordered = sorted(
                self.custom_occurrences,
                key=lambda occurrence: occurrence.start_at,
            )

            for previous, current in zip(
                ordered,
                ordered[1:],
            ):
                if current.start_at < previous.end_at:
                    raise ValueError(
                        "Les occurrences personnalisées ne doivent pas " "se chevaucher."
                    )

        return self


class PluginProgramCreate(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
    )

    code: str | None = Field(
        default=None,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    icon: str | None = Field(
        default=None,
        max_length=100,
    )

    color: str | None = Field(
        default=None,
        max_length=50,
    )

    position: int = Field(
        default=0,
        ge=0,
    )

    scope: ProgramScope = "GLOBAL"

    allow_user_use: bool = True

    allow_user_customization: bool = False

    allow_multiple_projects: bool = True

    allow_project_creation: bool = True

    configuration: dict[str, Any] = Field(
        default_factory=dict,
    )

    project_rules: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    resource_bindings: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    schedule: ProgramSchedule = Field(
        default_factory=ProgramSchedule,
    )


class PluginProgramUpdate(BaseModel):
    key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    code: str | None = Field(
        default=None,
        max_length=100,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    icon: str | None = Field(
        default=None,
        max_length=100,
    )

    color: str | None = Field(
        default=None,
        max_length=50,
    )

    position: int | None = Field(
        default=None,
        ge=0,
    )

    status: ProgramStatus | None = None

    is_active: bool | None = None

    scope: ProgramScope | None = None

    allow_user_use: bool | None = None

    allow_user_customization: bool | None = None

    allow_multiple_projects: bool | None = None

    allow_project_creation: bool | None = None

    configuration: dict[str, Any] | None = None

    project_rules: list[dict[str, Any]] | None = None

    resource_bindings: list[dict[str, Any]] | None = None

    schedule: ProgramSchedule | None = None


class PluginProgramResponse(BaseModel):
    id: int
    plugin_id: int

    key: str
    code: str | None

    name: str
    description: str | None

    icon: str | None
    color: str | None

    position: int

    status: str
    is_active: bool

    scope: str

    created_by: int
    owner_user_id: int | None

    allow_user_use: bool
    allow_user_customization: bool
    allow_multiple_projects: bool
    allow_project_creation: bool

    configuration: dict[str, Any]
    project_rules: list[dict[str, Any]]
    resource_bindings: list[dict[str, Any]]

    schedule: ProgramSchedule

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class PluginProgramListResponse(BaseModel):
    items: list[PluginProgramResponse]
    count: int
