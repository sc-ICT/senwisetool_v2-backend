from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PluginParametersBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class PluginAuthorizationDocument(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    instructions: str = Field(min_length=1, max_length=4000)
    required_elements: list[str] = Field(default_factory=list)
    required: bool = True
    allow_multiple_files: bool = False
    max_files: int = Field(default=1, ge=1, le=20)
    accepted_extensions: list[str] = Field(default_factory=list)
    max_file_size_mb: int = Field(default=20, gt=0, le=1024)
    issuer_required: bool = False
    document_number_required: bool = False
    issue_date_required: bool = False
    expiry_date_required: bool = False
    allow_expired_document: bool = False

    @model_validator(mode="after")
    def validate_document(self) -> "PluginAuthorizationDocument":
        if not self.allow_multiple_files and self.max_files != 1:
            raise ValueError(
                "max_files doit être égal à 1 lorsqu'un seul fichier est autorisé."
            )

        if self.allow_expired_document and not self.expiry_date_required:
            raise ValueError(
                "La date d'expiration doit être demandée lorsque les documents expirés sont autorisés."
            )

        return self


PluginAuthorizationFormFieldType = Literal[
    "TEXT",
    "TEXTAREA",
    "NUMBER",
    "EMAIL",
    "PHONE",
    "DATE",
    "DATETIME",
    "BOOLEAN",
    "SELECT",
    "MULTI_SELECT",
    "RADIO",
    "CHECKBOX",
    "FILE",
    "MULTI_FILE",
]


class PluginAuthorizationFormOption(BaseModel):
    value: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class PluginAuthorizationFormField(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    type: PluginAuthorizationFormFieldType = "TEXT"
    description: str | None = Field(default=None, max_length=2000)
    help_text: str | None = Field(default=None, max_length=1000)
    placeholder: str | None = Field(default=None, max_length=255)
    required: bool = False
    default_value: Any | None = None
    options: list[PluginAuthorizationFormOption] = Field(default_factory=list)
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=1)
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = Field(default=None, max_length=1000)
    accepted_extensions: list[str] = Field(default_factory=list)
    max_file_size_mb: int = Field(default=20, gt=0, le=1024)
    position: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_field(self) -> "PluginAuthorizationFormField":
        choice_types = {"SELECT", "MULTI_SELECT", "RADIO"}
        file_types = {"FILE", "MULTI_FILE"}

        if self.max_length is not None and self.min_length is not None:
            if self.max_length < self.min_length:
                raise ValueError(
                    f"Le champ « {self.key} » possède une longueur maximale inférieure à sa longueur minimale."
                )

        if self.max_value is not None and self.min_value is not None:
            if self.max_value < self.min_value:
                raise ValueError(
                    f"Le champ « {self.key} » possède une valeur maximale inférieure à sa valeur minimale."
                )

        if self.type in choice_types and not self.options:
            raise ValueError(
                f"Le champ « {self.key} » nécessite au moins une option."
            )

        if self.type in choice_types:
            option_values = [option.value for option in self.options]
            if len(option_values) != len(set(option_values)):
                raise ValueError(
                    f"Les valeurs des options du champ « {self.key} » doivent être uniques."
                )

        if self.type not in choice_types and self.options:
            raise ValueError(
                f"Le champ « {self.key} » ne peut pas contenir d'options pour ce type de champ."
            )

        if self.type not in file_types and self.accepted_extensions:
            raise ValueError(
                f"Le champ « {self.key} » ne peut pas définir d'extensions de fichiers."
            )

        if self.type not in {"TEXT", "TEXTAREA", "EMAIL", "PHONE"}:
            if self.min_length is not None or self.max_length is not None or self.pattern:
                raise ValueError(
                    f"Les contraintes textuelles du champ « {self.key} » ne sont pas compatibles avec son type."
                )

        if self.type != "NUMBER" and (
            self.min_value is not None or self.max_value is not None
        ):
            raise ValueError(
                f"Les contraintes numériques du champ « {self.key} » ne sont compatibles qu'avec NUMBER."
            )

        return self


class PluginAuthorizationForm(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    instructions: str = Field(min_length=1, max_length=4000)
    submit_label: str = Field(default="Soumettre la demande", min_length=1, max_length=100)
    success_message: str = Field(
        default="Votre demande d'autorisation a été soumise.",
        min_length=1,
        max_length=2000,
    )
    allow_save_draft: bool = False
    fields: list[PluginAuthorizationFormField] = Field(
        default_factory=list,
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_form(self) -> "PluginAuthorizationForm":
        keys = [field.key for field in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError(
                "Les clés des champs du formulaire d'autorisation doivent être uniques."
            )

        positions = [field.position for field in self.fields]
        if len(positions) != len(set(positions)):
            raise ValueError(
                "Les positions des champs du formulaire d'autorisation doivent être uniques."
            )

        return self


class PluginAcquisitionParameters(PluginParametersBase):
    availability: Literal["PUBLIC", "PRIVATE", "RESTRICTED"] = "PUBLIC"

    download_requires_approval: bool = False

    approval_mode: Literal[
        "SIMPLE_REQUEST",
        "FORM",
        "DOCUMENT",
        "FORM_AND_DOCUMENT",
    ] = "SIMPLE_REQUEST"

    authorization_form: PluginAuthorizationForm | None = None

    authorization_documents: list[PluginAuthorizationDocument] = Field(
        default_factory=list,
    )

    instructions_title: str | None = None

    instructions_description: str | None = None

    require_terms_acceptance: bool = False

    terms_url: str | None = None

    @model_validator(mode="after")
    def validate_approval_configuration(
        self,
    ) -> "PluginAcquisitionParameters":
        if not self.download_requires_approval:
            if self.approval_mode != "SIMPLE_REQUEST":
                raise ValueError(
                    "Le mode d'autorisation doit être SIMPLE_REQUEST lorsque le téléchargement ne nécessite pas d'autorisation."
                )

            if self.authorization_form is not None:
                raise ValueError(
                    "Le formulaire d'autorisation ne peut être défini que si l'autorisation au téléchargement est activée."
                )

            if self.authorization_documents:
                raise ValueError(
                    "Les documents d'autorisation ne peuvent être définis que si l'autorisation au téléchargement est activée."
                )

        if self.download_requires_approval:
            if self.approval_mode == "FORM" and self.authorization_form is None:
                raise ValueError(
                    "La définition du formulaire d'autorisation est obligatoire pour le mode FORM."
                )

            if self.approval_mode == "DOCUMENT" and not self.authorization_documents:
                raise ValueError(
                    "Au moins un document doit être défini pour le mode DOCUMENT."
                )

            if self.approval_mode == "FORM_AND_DOCUMENT":
                if self.authorization_form is None:
                    raise ValueError(
                        "La définition du formulaire d'autorisation est obligatoire pour le mode FORM_AND_DOCUMENT."
                    )

                if not self.authorization_documents:
                    raise ValueError(
                        "Au moins un document doit être défini pour le mode FORM_AND_DOCUMENT."
                    )

            if self.approval_mode == "SIMPLE_REQUEST":
                if self.authorization_form is not None or self.authorization_documents:
                    raise ValueError(
                        "Le mode SIMPLE_REQUEST ne doit pas contenir de formulaire ni de document configuré."
                    )

        if self.require_terms_acceptance and not self.terms_url:
            raise ValueError(
                "L'URL des conditions d'utilisation est obligatoire lorsque leur acceptation est requise."
            )

        document_keys = [document.key for document in self.authorization_documents]
        if len(document_keys) != len(set(document_keys)):
            raise ValueError(
                "Les clés des documents d'autorisation doivent être uniques."
            )

        return self


class PluginInstallationParameters(PluginParametersBase):
    activation_required: bool = True

    allow_auto_update: bool = True

    require_update_confirmation: bool = True

    allow_user_uninstall: bool = True

    max_active_installations: int | None = Field(
        default=None,
        gt=0,
    )


class PluginPermissionParameters(PluginParametersBase):
    enabled: bool = True

    require_authentication: bool = True

    allow_admin_override: bool = True

    allow_custom_roles: bool = False

    default_access: Literal[
        "DENY",
        "READ",
        "USE",
        "MANAGE",
    ] = "USE"

    allow_data_export: bool = True

    allow_data_import: bool = True

    allow_bulk_operations: bool = True

    allow_audit_log_access: bool = False


class PluginResourceParameters(PluginParametersBase):
    allow_global_read: bool = True

    allow_global_create: bool = False

    allow_global_update: bool = False

    allow_global_delete: bool = False

    allow_global_import: bool = False

    allow_global_export: bool = True

    allow_user_create: bool = True

    allow_user_update: bool = True

    allow_user_delete: bool = True

    allow_user_import: bool = True

    allow_user_export: bool = True

    allow_bulk_operations: bool = True

    require_delete_confirmation: bool = True

    allow_offline_editing: bool = True

    allow_schema_override: bool = True


class PluginProgramParameters(PluginParametersBase):
    enabled: bool = True

    allow_user_join: bool = True

    join_requires_approval: bool = False

    allow_user_leave: bool = True

    allow_user_create: bool = False

    allow_user_manage: bool = False

    allow_parallel_programs: bool = True

    allow_multiple_programs_per_user: bool = True

    allow_manual_start: bool = True

    allow_automatic_start: bool = True

    allow_recurring_schedule: bool = True


class PluginProjectParameters(PluginParametersBase):
    enabled: bool = True

    allow_user_create: bool = True

    creation_requires_approval: bool = False

    allow_user_customize: bool = True

    allow_resource_override: bool = True

    allow_form_override: bool = False

    allow_rules_override: bool = False

    allow_multiple_active_projects: bool = True

    allow_self_assignment: bool = False

    allow_supervisor_assignment: bool = True

    allow_project_archive: bool = True

    allow_project_delete: bool = False

    allow_offline_execution: bool = True


class PluginCollectionParameters(PluginParametersBase):
    enabled: bool = True

    allow_drafts: bool = True

    auto_save_drafts: bool = True

    auto_save_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
    )

    allow_partial_submission: bool = False

    require_validation_before_submission: bool = True

    require_submission_confirmation: bool = True

    allow_edit_after_submission: bool = False

    correction_requires_approval: bool = True

    allow_duplicate_submission: bool = False


class PluginMobileParameters(PluginParametersBase):
    enabled: bool = True

    offline_enabled: bool = True

    offline_allow_data_entry: bool = True

    offline_allow_data_edit: bool = True

    offline_allow_data_delete: bool = False

    max_offline_days: int | None = Field(
        default=30,
        gt=0,
    )

    automatic_sync: bool = True

    sync_wifi_only: bool = False

    sync_interval_seconds: int = Field(
        default=300,
        ge=30,
        le=86400,
    )

    retry_sync_on_failure: bool = True

    location_enabled: bool = True

    location_required_for_collection: bool = False

    location_required_for_submission: bool = False

    camera_enabled: bool = True

    file_upload_enabled: bool = True

    max_file_size_mb: int = Field(
        default=20,
        gt=0,
        le=1024,
    )

    allowed_file_extensions: list[str] = Field(
        default_factory=lambda: [
            "pdf",
            "jpg",
            "jpeg",
            "png",
        ],
    )

    notifications_enabled: bool = True


class PluginSecurityParameters(PluginParametersBase):
    session_max_idle_minutes: int = Field(
        default=60,
        gt=0,
    )

    encrypt_local_storage: bool = True

    encrypt_sensitive_fields: bool = True

    audit_enabled: bool = True

    audit_track_reads: bool = False

    audit_track_creates: bool = True

    audit_track_updates: bool = True

    audit_track_deletes: bool = True

    audit_track_exports: bool = True

    require_secure_device: bool = False

    block_rooted_or_modified_device: bool = False


class PluginPrivacyParameters(PluginParametersBase):
    allow_data_export: bool = True

    allow_data_deletion: bool = True

    retention_enabled: bool = False

    retention_days: int | None = Field(
        default=None,
        gt=0,
    )

    anonymize_after_retention: bool = False

    require_delete_confirmation: bool = True

    @model_validator(mode="after")
    def validate_retention(
        self,
    ) -> "PluginPrivacyParameters":

        if self.retention_enabled and self.retention_days is None:
            raise ValueError(
                "Le nombre de jours de conservation est obligatoire "
                "lorsque la conservation automatique est activée.",
            )

        return self


class PluginNotificationParameters(PluginParametersBase):
    enabled: bool = True

    notify_on_approval_request: bool = True

    notify_on_approval_decision: bool = True

    notify_on_sync_failure: bool = True

    notify_on_project_assignment: bool = True

    notify_on_submission: bool = True

    allow_push: bool = True

    allow_email: bool = True


class PluginLocalizationParameters(PluginParametersBase):
    default_language: str = "fr"

    supported_languages: list[str] = Field(
        default_factory=lambda: ["fr"],
    )

    timezone: str = "UTC"

    date_format: str = "DD/MM/YYYY"

    decimal_separator: Literal[".", ","] = ","


class PluginSupportParameters(PluginParametersBase):
    support_email: str | None = None

    support_url: str | None = None

    documentation_url: str | None = None

    report_issue_url: str | None = None


class PluginLegalParameters(PluginParametersBase):
    terms_url: str | None = None

    privacy_policy_url: str | None = None

    legal_notice_url: str | None = None

    license_name: str | None = None

    require_terms_acceptance_on_installation: bool = False


class PluginAdvancedParameters(PluginParametersBase):
    allow_experimental_features: bool = False

    debug_mode: bool = False

    expose_technical_errors: bool = False

    custom: dict[str, Any] = Field(
        default_factory=dict,
    )


class PluginParameters(PluginParametersBase):
    schema_version: int = Field(
        default=1,
        ge=1,
    )

    acquisition: PluginAcquisitionParameters = Field(
        default_factory=PluginAcquisitionParameters,
    )

    installation: PluginInstallationParameters = Field(
        default_factory=PluginInstallationParameters,
    )

    permissions: PluginPermissionParameters = Field(
        default_factory=PluginPermissionParameters,
    )

    resources: PluginResourceParameters = Field(
        default_factory=PluginResourceParameters,
    )

    programs: PluginProgramParameters = Field(
        default_factory=PluginProgramParameters,
    )

    projects: PluginProjectParameters = Field(
        default_factory=PluginProjectParameters,
    )

    collection: PluginCollectionParameters = Field(
        default_factory=PluginCollectionParameters,
    )

    mobile: PluginMobileParameters = Field(
        default_factory=PluginMobileParameters,
    )

    security: PluginSecurityParameters = Field(
        default_factory=PluginSecurityParameters,
    )

    privacy: PluginPrivacyParameters = Field(
        default_factory=PluginPrivacyParameters,
    )

    notifications: PluginNotificationParameters = Field(
        default_factory=PluginNotificationParameters,
    )

    localization: PluginLocalizationParameters = Field(
        default_factory=PluginLocalizationParameters,
    )

    support: PluginSupportParameters = Field(
        default_factory=PluginSupportParameters,
    )

    legal: PluginLegalParameters = Field(
        default_factory=PluginLegalParameters,
    )

    advanced: PluginAdvancedParameters = Field(
        default_factory=PluginAdvancedParameters,
    )
