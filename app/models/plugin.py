from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    PluginFieldType,
    PluginResourceScope,
    PluginStatus,
    PluginVersionStatus,
)

if TYPE_CHECKING:
    from app.models.form_builder.project import Project
    from app.models.plugin_resource_relation import PluginResourceRelation
    from app.models.user import User


# ============================================================================
# PLUGIN
# ============================================================================


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ========================================================================
    # IDENTIFICATION
    # ========================================================================

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # ========================================================================
    # PRESENTATION
    # ========================================================================

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    short_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    icon_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    banner_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ========================================================================
    # MARKETPLACE
    # ========================================================================

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    tags: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # ========================================================================
    # CONFIGURATION GENERALE
    # ========================================================================

    parameters: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    metadata_config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # ========================================================================
    # STATUS
    # ========================================================================

    status: Mapped[PluginStatus] = mapped_column(
        Enum(
            PluginStatus,
            name="plugin_status",
        ),
        nullable=False,
        default=PluginStatus.DRAFT,
        index=True,
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # ========================================================================
    # AUTHOR
    # ========================================================================

    created_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================================
    # DATES
    # ========================================================================

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    unpublished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    # ========================================================================
    # RELATIONS
    # ========================================================================

    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )

    versions: Mapped[list["PluginVersion"]] = relationship(
        "PluginVersion",
        back_populates="plugin",
        cascade="all, delete-orphan",
        order_by="PluginVersion.created_at.desc()",
        lazy="selectin",
    )

    resources: Mapped[list["PluginResource"]] = relationship(
        "PluginResource",
        back_populates="plugin",
        cascade="all, delete-orphan",
        order_by="PluginResource.position.asc()",
        lazy="selectin",
    )

    projects: Mapped[list["Project"]] = relationship(
        "Project",
        foreign_keys="Project.plugin_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ============================================================================
# PLUGIN VERSION
# ============================================================================


class PluginVersion(Base):
    """
    Version immuable d'un plugin.

    Une version DRAFT peut être préparée avant publication.

    Lorsqu'elle devient PUBLISHED, `definition` contient le snapshot complet
    de la configuration du plugin à cet instant.

    Une version PUBLISHED ne doit plus jamais être modifiée.
    """

    __tablename__ = "plugin_versions"

    __table_args__ = (
        UniqueConstraint(
            "plugin_id",
            "version",
            name="uq_plugin_versions_plugin_version",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ========================================================================
    # PLUGIN
    # ========================================================================

    plugin_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugins.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================================
    # VERSION
    # ========================================================================

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[PluginVersionStatus] = mapped_column(
        Enum(
            PluginVersionStatus,
            name="plugin_version_status",
        ),
        nullable=False,
        default=PluginVersionStatus.DRAFT,
        index=True,
    )

    # ========================================================================
    # IMMUTABLE SNAPSHOT
    # ========================================================================

    definition: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    definition_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # ========================================================================
    # RELEASE
    # ========================================================================

    release_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ========================================================================
    # DATES
    # ========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    # ========================================================================
    # RELATION
    # ========================================================================

    plugin: Mapped["Plugin"] = relationship(
        "Plugin",
        back_populates="versions",
        lazy="raise",
    )


# ============================================================================
# PLUGIN RESOURCE
# ============================================================================


class PluginResource(Base):
    """
    Ressource configurable d'un plugin.

    Exemples pour un plugin EUDR :

        PLANTER
        PLANTATION
        COOPERATIVE
        REQUIREMENT
        MARKET
        TRAINING
        INSPECTION

    Le moteur ne connait pas la signification métier de la ressource.
    Il ne connait que son schema et sa portée.
    """

    __tablename__ = "plugin_resources"

    __table_args__ = (
        UniqueConstraint(
            "plugin_id",
            "key",
            name="uq_plugin_resources_plugin_key",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ========================================================================
    # PLUGIN
    # ========================================================================

    plugin_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugins.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================================
    # IDENTIFICATION
    # ========================================================================

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================================
    # SCOPE
    # ========================================================================

    scope: Mapped[PluginResourceScope] = mapped_column(
        Enum(
            PluginResourceScope,
            name="plugin_resource_scope",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================================
    # USER CUSTOMIZATION
    # ========================================================================

    allow_user_schema_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # ========================================================================
    # SCHEMA
    # ========================================================================

    schema_definition: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # ========================================================================
    # DISPLAY
    # ========================================================================

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ========================================================================
    # STATUS
    # ========================================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # ========================================================================
    # DATES
    # ========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    # ========================================================================
    # RELATIONS
    # ========================================================================

    plugin: Mapped["Plugin"] = relationship(
        "Plugin",
        back_populates="resources",
        lazy="raise",
    )

    fields: Mapped[list["PluginResourceField"]] = relationship(
        "PluginResourceField",
        back_populates="resource",
        cascade="all, delete-orphan",
        order_by="PluginResourceField.position.asc()",
        lazy="selectin",
    )

    outgoing_relations: Mapped[list["PluginResourceRelation"]] = relationship(
        "PluginResourceRelation",
        foreign_keys="PluginResourceRelation.source_resource_id",
        back_populates="source_resource",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    incoming_relations: Mapped[list["PluginResourceRelation"]] = relationship(
        "PluginResourceRelation",
        foreign_keys="PluginResourceRelation.target_resource_id",
        back_populates="target_resource",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ============================================================================
# PLUGIN RESOURCE FIELD
# ============================================================================


class PluginResourceField(Base):
    """
    Champ du schema d'une ressource.

    Exemple :

        code
        name
        phone
        country
        sex
        age

    La définition du champ reste générique.
    """

    __tablename__ = "plugin_resource_fields"

    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "key",
            name="uq_plugin_resource_fields_resource_key",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    resource_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugin_resources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================================
    # IDENTIFICATION
    # ========================================================================

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================================
    # TYPE
    # ========================================================================

    field_type: Mapped[PluginFieldType] = mapped_column(
        Enum(
            PluginFieldType,
            name="plugin_field_type",
        ),
        nullable=False,
    )

    # ========================================================================
    # VALIDATION
    # ========================================================================

    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    min_length: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    max_length: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    min_value: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    max_value: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    pattern: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ========================================================================
    # CHOICE
    # ========================================================================

    options: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # ========================================================================
    # DEFAULT
    # ========================================================================

    default_value: Mapped[object | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # ========================================================================
    # DISPLAY
    # ========================================================================

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # ========================================================================
    # DATES
    # ========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    # ========================================================================
    # RELATION
    # ========================================================================

    resource: Mapped["PluginResource"] = relationship(
        "PluginResource",
        back_populates="fields",
        lazy="raise",
    )
