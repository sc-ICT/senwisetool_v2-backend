from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    PluginStatus,
    PluginVersionStatus,
)
from app.models.plugin import (
    Plugin,
    PluginResource,
    PluginResourceField,
    PluginVersion,
)
from app.schemas.plugin import (
    PluginCreate,
    PluginUpdate,
)


class PluginService:

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    # ========================================================================
    # VERSION SNAPSHOT
    # ========================================================================

    @staticmethod
    def _canonical_json(
        value: dict,
    ) -> str:
        """
        Transforme une définition en JSON canonique.

        Le même contenu produit toujours exactement la même chaîne JSON.
        """

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _hash_definition(
        cls,
        definition: dict,
    ) -> str:
        """
        Calcule le SHA-256 de la définition canonique.
        """

        canonical = cls._canonical_json(
            definition,
        )

        return hashlib.sha256(
            canonical.encode("utf-8"),
        ).hexdigest()

    @staticmethod
    def _serialize_field(
        field: PluginResourceField,
    ) -> dict[str, Any]:
        """
        Transforme un PluginResourceField SQLAlchemy en dictionnaire
        indépendant de SQLAlchemy.

        Ce contenu fera partie du snapshot de la version.
        """

        return {
            "key": field.key,
            "label": field.label,
            "description": field.description,
            "field_type": field.field_type.value,
            "required": field.required,
            "min_length": field.min_length,
            "max_length": field.max_length,
            "min_value": field.min_value,
            "max_value": field.max_value,
            "pattern": field.pattern,
            "options": field.options or [],
            "default_value": field.default_value,
            "position": field.position,
            "is_active": field.is_active,
        }

    @classmethod
    def _serialize_resource(
        cls,
        resource: PluginResource,
    ) -> dict[str, Any]:
        """
        Transforme une ressource complète en définition indépendante.

        Les IDs techniques de la base ne sont volontairement pas exposés
        dans le snapshot.
        """

        fields = sorted(
            resource.fields,
            key=lambda field: (
                field.position,
                field.key,
            ),
        )

        return {
            "key": resource.key,
            "name": resource.name,
            "description": resource.description,
            "scope": resource.scope.value,
            "allow_user_schema_override": (resource.allow_user_schema_override),
            "schema_definition": resource.schema_definition or {},
            "position": resource.position,
            "icon": resource.icon,
            "is_active": resource.is_active,
            "fields": [cls._serialize_field(field) for field in fields],
        }

    @classmethod
    def _build_plugin_definition(
        cls,
        plugin: Plugin,
    ) -> dict[str, Any]:
        """
        Construit le snapshot complet de la configuration du plugin.

        Cette définition est la source de vérité de la release publiée.
        """

        resources = sorted(
            plugin.resources,
            key=lambda resource: (
                resource.position,
                resource.key,
            ),
        )

        return {
            "schema_version": 1,
            "plugin": {
                "code": plugin.code,
                "name": plugin.name,
                "slug": plugin.slug,
                "description": plugin.description,
                "short_description": plugin.short_description,
                "icon_url": plugin.icon_url,
                "banner_url": plugin.banner_url,
                "category": plugin.category,
                "tags": plugin.tags or [],
            },
            "configuration": {
                "parameters": plugin.parameters or {},
                "metadata_config": plugin.metadata_config or {},
            },
            "resources": [cls._serialize_resource(resource) for resource in resources],
        }

    @classmethod
    def _build_version_snapshot(
        cls,
        plugin: Plugin,
    ) -> tuple[dict, str]:
        """
        Construit le snapshot et son hash.
        """

        definition = cls._build_plugin_definition(
            plugin,
        )

        definition_hash = cls._hash_definition(
            definition,
        )

        return (
            definition,
            definition_hash,
        )

    @staticmethod
    def _assert_version_mutable(
        version: PluginVersion,
    ) -> None:
        """
        Une version publiée est immuable.
        """

        if version.status == PluginVersionStatus.PUBLISHED:
            raise ValueError(
                "Une version publiée est immuable et ne peut plus être modifiée.",
            )

        if version.status == PluginVersionStatus.DEPRECATED:
            raise ValueError(
                "Une version dépréciée est immuable et ne peut plus être modifiée.",
            )

    # ========================================================================
    # GET
    # ========================================================================

    async def get(
        self,
        *,
        plugin_id: int,
    ) -> Plugin | None:
        result = await self.session.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.versions),
                selectinload(
                    Plugin.resources,
                ).selectinload(
                    PluginResource.fields,
                ),
            )
            .where(
                Plugin.id == plugin_id,
            )
        )

        return result.scalar_one_or_none()

    # ========================================================================
    # GET VERSION
    # ========================================================================

    async def get_version(
        self,
        *,
        plugin_id: int,
        version_id: int,
    ) -> PluginVersion | None:

        result = await self.session.execute(
            select(PluginVersion).where(
                PluginVersion.id == version_id,
                PluginVersion.plugin_id == plugin_id,
            )
        )

        return result.scalar_one_or_none()

    # ========================================================================
    # GET BY CODE
    # ========================================================================

    async def get_by_code(
        self,
        *,
        code: str,
    ) -> Plugin | None:
        result = await self.session.execute(
            select(Plugin).where(
                Plugin.code == code,
            )
        )

        return result.scalar_one_or_none()

    # ========================================================================
    # GET BY SLUG
    # ========================================================================

    async def get_by_slug(
        self,
        *,
        slug: str,
    ) -> Plugin | None:
        result = await self.session.execute(
            select(Plugin).where(
                Plugin.slug == slug,
            )
        )

        return result.scalar_one_or_none()

    # ========================================================================
    # CODE
    # ========================================================================

    @staticmethod
    def _generate_code_base(
        name: str,
    ) -> str:
        code = name.strip().upper()

        code = re.sub(
            r"[^A-Z0-9]+",
            "_",
            code,
        )

        code = re.sub(
            r"_+",
            "_",
            code,
        )

        code = code.strip("_")

        if not code:
            raise ValueError(
                "Impossible de générer le code du plugin.",
            )

        return f"PLUGIN_{code}"[:100]

    async def _generate_unique_code(
        self,
        base_code: str,
    ) -> str:
        existing = await self.get_by_code(
            code=base_code,
        )

        if existing is None:
            return base_code

        counter = 2

        while True:
            suffix = f"_{counter}"

            candidate = f"{base_code[:100 - len(suffix)]}{suffix}"

            existing = await self.get_by_code(
                code=candidate,
            )

            if existing is None:
                return candidate

            counter += 1

    # ========================================================================
    # SLUG
    # ========================================================================

    @staticmethod
    def _generate_slug(
        name: str,
    ) -> str:
        slug = name.strip().lower()

        slug = re.sub(
            r"[^\w\s-]",
            "",
            slug,
            flags=re.UNICODE,
        )

        slug = re.sub(
            r"[-\s]+",
            "-",
            slug,
        )

        slug = slug.strip("-")

        if not slug:
            raise ValueError(
                "Impossible de générer le slug du plugin.",
            )

        return slug[:255]

    async def _generate_unique_slug(
        self,
        base_slug: str,
    ) -> str:
        counter = 2

        while True:
            candidate = f"{base_slug}-{counter}"

            existing = await self.get_by_slug(
                slug=candidate,
            )

            if existing is None:
                return candidate

            counter += 1

    # ========================================================================
    # LIST
    # ========================================================================

    async def list(
        self,
        *,
        include_archived: bool = False,
    ) -> list[Plugin]:
        query = select(Plugin).options(
            selectinload(Plugin.versions),
            selectinload(
                Plugin.resources,
            ).selectinload(
                PluginResource.fields,
            ),
        )

        if not include_archived:
            query = query.where(
                Plugin.status != PluginStatus.ARCHIVED,
            )

        query = query.order_by(
            Plugin.created_at.desc(),
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create(
        self,
        *,
        user_id: int,
        data: PluginCreate,
    ) -> Plugin:

        code_base = self._generate_code_base(
            data.name,
        )

        code = await self._generate_unique_code(
            code_base,
        )

        slug = self._generate_slug(
            data.name,
        )

        existing_slug = await self.get_by_slug(
            slug=slug,
        )

        if existing_slug is not None:
            slug = await self._generate_unique_slug(
                slug,
            )

        plugin = Plugin(
            code=code,
            name=data.name.strip(),
            slug=slug,
            description=data.description,
            short_description=data.short_description,
            icon_url=data.icon_url,
            banner_url=data.banner_url,
            category=data.category,
            tags=data.tags,
            parameters=data.parameters,
            metadata_config=data.metadata_config,
            status=PluginStatus.DRAFT,
            is_public=False,
            created_by=user_id,
        )

        self.session.add(plugin)

        await self.session.flush()

        # --------------------------------------------------------------------
        # Première version
        # --------------------------------------------------------------------

        version = PluginVersion(
            plugin_id=plugin.id,
            version=data.initial_version,
            status=PluginVersionStatus.DRAFT,
            definition={},
            definition_hash=None,
            release_notes=data.release_notes,
        )

        self.session.add(version)

        await self.session.flush()

        # --------------------------------------------------------------------
        # Rechargement
        # --------------------------------------------------------------------

        return await self._reload_plugin(
            plugin_id=plugin.id,
        )

    # ========================================================================
    # UPDATE
    # ========================================================================

    async def update(
        self,
        *,
        plugin_id: int,
        data: PluginUpdate,
    ) -> Plugin:

        plugin = await self.get(
            plugin_id=plugin_id,
        )

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        # --------------------------------------------------------------------
        # Uniquement les brouillons peuvent être modifiés.
        # --------------------------------------------------------------------

        self._ensure_editable(
            plugin,
        )

        # --------------------------------------------------------------------
        # Mise à jour
        # --------------------------------------------------------------------

        if data.name is not None:
            plugin.name = data.name.strip()

        if data.description is not None:
            plugin.description = data.description.strip()

        if data.short_description is not None:
            plugin.short_description = data.short_description.strip() or None

        if data.icon_url is not None:
            plugin.icon_url = data.icon_url.strip() or None

        if data.banner_url is not None:
            plugin.banner_url = data.banner_url.strip() or None

        if data.category is not None:
            plugin.category = data.category.strip() or None

        if data.tags is not None:
            plugin.tags = data.tags

        if data.parameters is not None:
            plugin.parameters = data.parameters

        if data.metadata_config is not None:
            plugin.metadata_config = data.metadata_config

        await self.session.flush()

        return await self._reload_plugin(
            plugin_id=plugin.id,
        )

    # ========================================================================
    # DELETE
    # ========================================================================

    async def delete(
        self,
        *,
        plugin_id: int,
    ) -> None:

        plugin = await self.get(
            plugin_id=plugin_id,
        )

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        # --------------------------------------------------------------------
        # Un plugin publié ne peut pas être supprimé.
        # --------------------------------------------------------------------

        if plugin.status == PluginStatus.PUBLISHED:
            raise ValueError(
                "Un plugin publié ne peut pas être supprimé. " "Dépubliez-le d'abord.",
            )

        # --------------------------------------------------------------------
        # Un plugin archivé ne peut pas être supprimé.
        # --------------------------------------------------------------------

        if plugin.status == PluginStatus.ARCHIVED:
            raise ValueError(
                "Un plugin archivé ne peut pas être supprimé.",
            )

        await self.session.delete(plugin)

        await self.session.flush()

    # ========================================================================
    # PUBLISH
    # ========================================================================

    async def publish(
        self,
        *,
        plugin_id: int,
    ) -> Plugin:

        plugin = await self.get(
            plugin_id=plugin_id,
        )

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        # --------------------------------------------------------------------
        # Le plugin doit être en DRAFT.
        # --------------------------------------------------------------------

        if plugin.status != PluginStatus.DRAFT:
            raise ValueError(
                "Seul un plugin en brouillon peut être publié.",
            )

        # --------------------------------------------------------------------
        # Recherche de la version DRAFT.
        # --------------------------------------------------------------------

        draft_versions = [
            version for version in plugin.versions if version.status == PluginVersionStatus.DRAFT
        ]

        if not draft_versions:
            raise ValueError(
                "Le plugin ne possède aucune version en brouillon " "à publier.",
            )

        if len(draft_versions) > 1:
            raise ValueError(
                "Le plugin possède plusieurs versions en brouillon. "
                "Une seule version peut être publiée à la fois.",
            )

        version = draft_versions[0]

        # --------------------------------------------------------------------
        # Protection supplémentaire.
        # --------------------------------------------------------------------

        self._assert_version_mutable(
            version,
        )

        # --------------------------------------------------------------------
        # Construction du snapshot.
        #
        # IMPORTANT :
        # Le snapshot est construit AVANT de changer les statuts.
        # --------------------------------------------------------------------

        definition, definition_hash = self._build_version_snapshot(
            plugin,
        )

        now = datetime.now(
            timezone.utc,
        )

        # --------------------------------------------------------------------
        # Stockage du snapshot.
        # --------------------------------------------------------------------

        version.definition = definition
        version.definition_hash = definition_hash

        # --------------------------------------------------------------------
        # Publication de la version.
        # --------------------------------------------------------------------

        version.status = PluginVersionStatus.PUBLISHED
        version.published_at = now
        version.deprecated_at = None

        # --------------------------------------------------------------------
        # Publication du plugin.
        # --------------------------------------------------------------------

        plugin.status = PluginStatus.PUBLISHED
        plugin.is_public = True
        plugin.published_at = now
        plugin.unpublished_at = None

        await self.session.flush()

        # --------------------------------------------------------------------
        # Rechargement.
        # --------------------------------------------------------------------

        return await self._reload_plugin(
            plugin_id=plugin.id,
        )

    # ========================================================================
    # UNPUBLISH
    # ========================================================================

    async def unpublish(
        self,
        *,
        plugin_id: int,
    ) -> Plugin:

        plugin = await self.get(
            plugin_id=plugin_id,
        )

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        # --------------------------------------------------------------------
        # Seul un plugin publié peut être dépublié.
        # --------------------------------------------------------------------

        if plugin.status != PluginStatus.PUBLISHED:
            raise ValueError(
                "Seul un plugin publié peut être dépublié.",
            )

        now = datetime.now(timezone.utc)

        plugin.status = PluginStatus.UNPUBLISHED
        plugin.is_public = False
        plugin.unpublished_at = now

        await self.session.flush()

        return await self._reload_plugin(
            plugin_id=plugin.id,
        )

    # ========================================================================
    # MOVE TO DRAFT
    # ========================================================================

    async def move_to_draft(
        self,
        *,
        plugin_id: int,
    ) -> Plugin:

        plugin = await self.get(
            plugin_id=plugin_id,
        )

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        # --------------------------------------------------------------------
        # Un plugin publié doit d'abord être dépublié.
        # --------------------------------------------------------------------

        if plugin.status == PluginStatus.PUBLISHED:
            raise ValueError(
                "Un plugin publié doit d'abord être dépublié "
                "avant de pouvoir être remis en brouillon.",
            )

        # --------------------------------------------------------------------
        # Seuls UNPUBLISHED et ARCHIVED peuvent revenir en DRAFT.
        # --------------------------------------------------------------------

        if plugin.status not in (
            PluginStatus.UNPUBLISHED,
            PluginStatus.ARCHIVED,
        ):
            raise ValueError(
                "Seuls les plugins dépubliés ou archivés " "peuvent être remis en brouillon.",
            )

        # --------------------------------------------------------------------
        # Vérifier qu'il n'existe pas déjà une version DRAFT.
        # --------------------------------------------------------------------

        draft_versions = [
            version for version in plugin.versions if version.status == PluginVersionStatus.DRAFT
        ]

        if draft_versions:
            raise ValueError(
                "Le plugin possède déjà une version en brouillon.",
            )

        # --------------------------------------------------------------------
        # Dernière version publiée / dépréciée.
        # --------------------------------------------------------------------

        versions = sorted(
            plugin.versions,
            key=lambda version: version.created_at,
            reverse=True,
        )

        if not versions:
            raise ValueError(
                "Le plugin ne possède aucune version.",
            )

        current_version = versions[0]

        # --------------------------------------------------------------------
        # Calcul de la prochaine version.
        # --------------------------------------------------------------------

        next_version = self._next_version(
            current_version.version,
        )

        # --------------------------------------------------------------------
        # Création du nouveau DRAFT.
        #
        # IMPORTANT :
        # On ne modifie JAMAIS current_version.
        # --------------------------------------------------------------------

        new_version = PluginVersion(
            plugin_id=plugin.id,
            version=next_version,
            status=PluginVersionStatus.DRAFT,
            definition={},
            definition_hash=None,
            release_notes=None,
        )

        self.session.add(
            new_version,
        )

        # --------------------------------------------------------------------
        # Plugin DRAFT.
        # --------------------------------------------------------------------

        plugin.status = PluginStatus.DRAFT
        plugin.is_public = False

        await self.session.flush()

        return await self._reload_plugin(
            plugin_id=plugin.id,
        )

    # ========================================================================
    # ARCHIVE
    # ========================================================================

    async def archive(
        self,
        *,
        plugin_id: int,
    ) -> Plugin:

        plugin = await self.get(
            plugin_id=plugin_id,
        )

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        # --------------------------------------------------------------------
        # Un plugin publié doit d'abord être dépublié.
        # --------------------------------------------------------------------

        if plugin.status == PluginStatus.PUBLISHED:
            raise ValueError(
                "Un plugin publié doit d'abord être dépublié " "avant d'être archivé.",
            )

        # --------------------------------------------------------------------
        # Un plugin déjà archivé ne peut pas être archivé.
        # --------------------------------------------------------------------

        if plugin.status == PluginStatus.ARCHIVED:
            raise ValueError(
                "Ce plugin est déjà archivé.",
            )

        plugin.status = PluginStatus.ARCHIVED
        plugin.is_public = False

        await self.session.flush()

        return await self._reload_plugin(
            plugin_id=plugin.id,
        )

    # ========================================================================
    # INTERNAL VALIDATION
    # ========================================================================

    # ========================================================================
    # VERSIONING
    # ========================================================================

    @staticmethod
    def _next_version(
        version: str,
    ) -> str:
        """
        Calcule la prochaine version patch.

        Exemples :

            1.0.0 -> 1.0.1
            1.2.3 -> 1.2.4
            2.0.0 -> 2.0.1

        Si la version n'est pas strictement semver, on refuse
        automatiquement afin d'éviter de créer des versions ambiguës.
        """

        value = version.strip()

        match = re.fullmatch(
            r"(\d+)\.(\d+)\.(\d+)",
            value,
        )

        if match is None:
            raise ValueError(
                "La version du plugin doit respecter le format "
                "MAJOR.MINOR.PATCH, par exemple 1.0.0.",
            )

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))

        return f"{major}.{minor}.{patch + 1}"

    @staticmethod
    def _ensure_editable(
        plugin: Plugin,
    ) -> None:

        if plugin.status != PluginStatus.DRAFT:
            raise ValueError(
                f"Un plugin {plugin.status} ne peut plus être modifié. "
                "Seuls les plugins en brouillon peuvent être modifiés.",
            )

    # ========================================================================
    # INTERNAL RELOAD
    # ========================================================================

    async def _reload_plugin(
        self,
        *,
        plugin_id: int,
    ) -> Plugin:

        result = await self.session.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.versions),
                selectinload(
                    Plugin.resources,
                ).selectinload(
                    PluginResource.fields,
                ),
            )
            .where(
                Plugin.id == plugin_id,
            )
        )

        plugin = result.scalar_one_or_none()

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        return plugin

    # ========================================================================
    # VERSION INTEGRITY
    # ========================================================================

    @classmethod
    def verify_version_integrity(
        cls,
        version: PluginVersion,
    ) -> bool:
        """
        Vérifie que la définition stockée correspond au hash enregistré.
        """

        if not version.definition_hash:
            return False

        calculated_hash = cls._hash_definition(
            version.definition,
        )

        return calculated_hash == version.definition_hash
