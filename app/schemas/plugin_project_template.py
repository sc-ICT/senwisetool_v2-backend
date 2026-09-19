from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ============================================================================
# RESOURCE USAGE
# ============================================================================

ProjectResourceUsage = Literal[
    "GENERAL",
    "QUESTION",
    "SELECTION",
    "LOOKUP",
    "CALCULATION",
]


# ============================================================================
# QUESTION RESPONSE
# ============================================================================

ProjectQuestionResponseMode = Literal[
    "DEFERRED",
    "FIXED",
    "ALLOWED",
]

QuestionType = Literal[
    "TEXT",
    "LONG_TEXT",
    "EMAIL",
    "PHONE",
    "URL",
    "ADDRESS",
    "INTEGER",
    "DECIMAL",
    "PERCENTAGE",
    "CURRENCY",
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "DROPDOWN",
    "AUTOCOMPLETE",
    "RATING",
    "LIKERT_SCALE",
    "RANKING",
    "DATE",
    "TIME",
    "DATETIME",
    "DURATION",
    "POINT",
    "LINE",
    "POLYGON",
    "AREA",
    "PHOTO",
    "VIDEO",
    "AUDIO",
    "FILE",
    "SIGNATURE",
    "QR_CODE",
    "BARCODE",
    "ENTITY_SELECT",
    "ENTITY_SEARCH",
    "CALCULATION",
    "NOTE",
    "CONSENT",
    "HIDDEN",
]


# ============================================================================
# QUESTION RESPONSE OPTION
# ============================================================================


class ProjectQuestionResponseOption(BaseModel):
    value: str = Field(
        min_length=1,
        max_length=255,
    )

    label: str = Field(
        min_length=1,
        max_length=255,
    )

    position: int = Field(
        default=0,
        ge=0,
    )

    is_active: bool = True

    statistics: dict[str, Any] = Field(
        default_factory=dict,
    )


# ============================================================================
# QUESTION RESPONSE OPTION SOURCE
# ============================================================================

ProjectQuestionResponseOptionsSource = Literal[
    "MANUAL",
    "RESOURCE",
]


class ProjectQuestionResponseResourceOptions(BaseModel):
    resource_id: int = Field(gt=0)

    value_field_key: str = Field(
        min_length=1,
        max_length=100,
    )

    label_field_key: str = Field(
        min_length=1,
        max_length=100,
    )


# ============================================================================
# QUESTION RESPONSE CONFIGURATION
# ============================================================================


class ProjectQuestionResponseConfiguration(BaseModel):
    mode: ProjectQuestionResponseMode = "DEFERRED"

    types: list[QuestionType] = Field(
        default_factory=list,
    )

    options_source: ProjectQuestionResponseOptionsSource = "MANUAL"

    resource_options: ProjectQuestionResponseResourceOptions | None = None

    options: list[ProjectQuestionResponseOption] = Field(
        default_factory=list,
    )

    allow_option_customization: bool = True

    allow_type_override: bool = True

    @model_validator(mode="after")
    def validate_response_configuration(
        self,
    ) -> "ProjectQuestionResponseConfiguration":

        if self.mode == "DEFERRED":
            if self.types:
                raise ValueError(
                    "Une configuration de réponse DEFERRED "
                    "ne doit pas définir de types de réponse."
                )
        elif self.mode == "FIXED":
            if len(self.types) != 1:
                raise ValueError(
                    "Une configuration FIXED doit définir exactement un type de réponse."
                )
        elif self.mode == "ALLOWED":
            if not self.types:
                raise ValueError(
                    "Une configuration ALLOWED doit définir au moins un type de réponse."
                )

        choice_types = {
            "SINGLE_CHOICE",
            "MULTIPLE_CHOICE",
            "DROPDOWN",
            "AUTOCOMPLETE",
        }

        if self.options_source == "RESOURCE":
            if not any(response_type in choice_types for response_type in self.types):
                raise ValueError(
                    "Une source d'options ne peut être utilisée que pour "
                    "un type de réponse à choix."
                )

            if self.resource_options is None:
                raise ValueError(
                    "Une source d'options RESOURCE doit définir "
                    "la ressource et les champs valeur/libellé."
                )
        else:
            if self.resource_options is not None:
                raise ValueError(
                    "Une configuration d'options MANUAL ne doit pas définir " "de ressource source."
                )

        positions = [option.position for option in self.options]

        if len(positions) != len(set(positions)):
            raise ValueError("Les positions des options de réponse doivent être uniques.")

        values = [option.value for option in self.options]

        if len(values) != len(set(values)):
            raise ValueError("Les valeurs des options de réponse doivent être uniques.")

        return self


# ============================================================================
# QUESTION HIERARCHY
# ============================================================================


class ProjectResourceQuestionHierarchyLevel(BaseModel):
    relation_id: int = Field(
        gt=0,
    )

    resource_id: int = Field(
        gt=0,
    )

    resource_key: str | None = None

    resource_name: str | None = None

    source_field_key: str = Field(
        min_length=1,
        max_length=100,
    )

    target_field_key: str = Field(
        min_length=1,
        max_length=100,
    )

    label: str | None = Field(
        default=None,
        max_length=255,
    )

    position: int = Field(
        ge=0,
    )


# ============================================================================
# QUESTION DISPLAY
# ============================================================================


class ProjectResourceQuestionDisplayConfiguration(BaseModel):
    question_field_key: str = Field(
        min_length=1,
        max_length=100,
    )

    question_key_field_key: str | None = Field(
        default=None,
        max_length=100,
    )

    title_field_key: str | None = Field(
        default=None,
        max_length=100,
    )

    hierarchy: list[ProjectResourceQuestionHierarchyLevel] = Field(
        default_factory=list,
    )

    group_by_hierarchy: bool = True

    show_question_key: bool = False

    @model_validator(mode="after")
    def validate_hierarchy_positions(
        self,
    ) -> "ProjectResourceQuestionDisplayConfiguration":

        positions = [level.position for level in self.hierarchy]

        expected = list(
            range(
                len(
                    self.hierarchy,
                )
            )
        )

        if sorted(positions) != expected:
            raise ValueError(
                "Les positions de la hiérarchie doivent " "commencer à 0 et être continues."
            )

        return self


# ============================================================================
# QUESTION STATISTICS
# ============================================================================

ProjectQuestionStatisticsMeasure = Literal[
    "COUNT",
    "PERCENTAGE",
]

ProjectQuestionStatisticsPercentageDenominator = Literal[
    "ALL_QUESTIONS",
    "ANSWERED_QUESTIONS",
    "EXCLUDE_VALUES",
]


class ProjectQuestionStatisticsCategory(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
    )

    label: str = Field(
        min_length=1,
        max_length=255,
    )

    response_values: list[str] = Field(
        default_factory=list,
    )

    excluded_from_percentage: bool = False

    position: int = Field(
        default=0,
        ge=0,
    )

    is_active: bool = True


class ProjectQuestionStatisticsConfiguration(BaseModel):
    enabled: bool = False

    realtime: bool = True

    global_: bool = Field(
        default=True,
        alias="global",
    )

    hierarchy_levels: list[int] = Field(
        default_factory=list,
        min_length=0,
    )

    measures: list[ProjectQuestionStatisticsMeasure] = Field(
        default_factory=lambda: [
            "COUNT",
            "PERCENTAGE",
        ],
    )

    percentage_denominator: ProjectQuestionStatisticsPercentageDenominator = "ANSWERED_QUESTIONS"

    excluded_response_values: list[str] = Field(
        default_factory=list,
    )

    categories: list[ProjectQuestionStatisticsCategory] = Field(
        default_factory=list,
    )

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def validate_statistics(
        self,
    ) -> "ProjectQuestionStatisticsConfiguration":

        if "PERCENTAGE" in self.measures:

            if not self.global_ and not self.hierarchy_levels:
                raise ValueError(
                    "Les statistiques de type PERCENTAGE "
                    "doivent être calculées au moins à un niveau."
                )

        if self.percentage_denominator == "EXCLUDE_VALUES":
            if not self.excluded_response_values:
                raise ValueError(
                    "Au moins une valeur doit être exclue "
                    "lorsque le dénominateur est EXCLUDE_VALUES."
                )

        return self


# ============================================================================
# COMPLETE QUESTION CONFIGURATION
# ============================================================================


class ProjectResourceQuestionConfiguration(BaseModel):
    display: ProjectResourceQuestionDisplayConfiguration

    response: ProjectQuestionResponseConfiguration = Field(
        default_factory=ProjectQuestionResponseConfiguration,
    )

    statistics: ProjectQuestionStatisticsConfiguration = Field(
        default_factory=ProjectQuestionStatisticsConfiguration,
    )


# ============================================================================
# RESOURCE BINDING
# ============================================================================


class ProjectResourceBinding(BaseModel):
    resource_id: int = Field(
        gt=0,
    )

    resource_key: str | None = None

    usage: ProjectResourceUsage

    required: bool = False

    configuration: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_usage_configuration(
        self,
    ) -> "ProjectResourceBinding":

        if self.usage == "QUESTION":

            configuration = ProjectResourceQuestionConfiguration.model_validate(
                self.configuration,
            )

            self.configuration = configuration.model_dump(
                mode="json",
                by_alias=True,
            )

        return self


# ============================================================================
# PROJECT TEMPLATE
# ============================================================================


class PluginProjectTemplateCreate(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    project_type: str = Field(
        min_length=1,
        max_length=100,
    )

    program_id: int | None = None

    icon: str | None = None

    position: int = 0

    allow_user_use: bool = True

    allow_user_customization: bool = False

    configuration: dict[str, Any] = Field(
        default_factory=dict,
    )

    rules: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    resource_bindings: list[ProjectResourceBinding] = Field(
        default_factory=list,
    )

    metrics: list[dict[str, Any]] = Field(
        default_factory=list,
    )


class PluginProjectTemplateUpdate(BaseModel):
    key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    project_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    program_id: int | None = None

    icon: str | None = None

    position: int | None = None

    is_active: bool | None = None

    allow_user_use: bool | None = None

    allow_user_customization: bool | None = None

    configuration: dict[str, Any] | None = None

    rules: list[dict[str, Any]] | None = None

    resource_bindings: list[ProjectResourceBinding] | None = None

    metrics: list[dict[str, Any]] | None = None


# ============================================================================
# RESPONSE
# ============================================================================


class PluginProjectTemplateResponse(BaseModel):
    id: int

    plugin_id: int

    key: str

    name: str

    description: str | None

    project_type: str

    program_id: int | None

    icon: str | None

    position: int

    is_active: bool

    allow_user_use: bool

    allow_user_customization: bool

    configuration: dict[str, Any]

    rules: list[dict[str, Any]]

    resource_bindings: list[ProjectResourceBinding]

    metrics: list[dict[str, Any]]

    model_config = ConfigDict(
        from_attributes=True,
    )


class PluginProjectTemplateListResponse(BaseModel):
    items: list[PluginProjectTemplateResponse]

    count: int
