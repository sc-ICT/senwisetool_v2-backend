from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    PluginFieldType,
    PluginResourceScope,
    PluginStatus,
)
from app.models.plugin import (
    Plugin,
    PluginResource,
    PluginResourceField,
)
from app.models.plugin_resource_data import (
    PluginResourceRecord,
    PluginResourceUserSchema,
)
from app.models.plugin_resource_relation import PluginResourceRelation
from app.schemas.plugin_resource import (
    PluginResourceCreate,
    PluginResourceFieldCreate,
    PluginResourceFieldUpdate,
    PluginResourceRecordCreate,
    PluginResourceRecordUpdate,
    PluginResourceRelationCreate,
    PluginResourceUpdate,
    PluginResourceUserSchemaUpdate,
)


class PluginResourceService:

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    # ========================================================================
    # RESOURCE
    # ========================================================================

    async def get(
        self,
        *,
        resource_id: int,
    ) -> PluginResource | None:

        result = await self.session.execute(
            select(PluginResource)
            .options(
                selectinload(
                    PluginResource.fields,
                ),
            )
            .where(
                PluginResource.id == resource_id,
            )
        )

        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        plugin_id: int,
    ) -> list[PluginResource]:

        result = await self.session.execute(
            select(PluginResource)
            .options(
                selectinload(
                    PluginResource.fields,
                ),
            )
            .where(
                PluginResource.plugin_id == plugin_id,
            )
            .order_by(
                PluginResource.position.asc(),
                PluginResource.created_at.asc(),
            )
        )

        return list(result.scalars().all())

    async def _get_resource_or_fail(
        self,
        *,
        resource_id: int,
    ) -> PluginResource:

        resource = await self.get(
            resource_id=resource_id,
        )

        if resource is None:
            raise ValueError(
                "Ressource introuvable.",
            )

        return resource

    async def _get_plugin(
        self,
        *,
        plugin_id: int,
    ) -> Plugin:

        result = await self.session.execute(
            select(Plugin).where(
                Plugin.id == plugin_id,
            )
        )

        plugin = result.scalar_one_or_none()

        if plugin is None:
            raise ValueError(
                "Plugin introuvable.",
            )

        return plugin

    async def _validate_record_relations(
        self,
        *,
        resource: PluginResource,
        data: dict[str, Any],
        user_id: int,
        owner_id: int | None,
        is_admin: bool,
        exclude_record_id: int | None = None,
        pending_records: list[dict[str, Any]] | None = None,
    ) -> None:

        result = await self.session.execute(
            select(PluginResourceRelation).where(
                PluginResourceRelation.is_active.is_(True),
                or_(
                    PluginResourceRelation.source_resource_id == resource.id,
                    PluginResourceRelation.target_resource_id == resource.id,
                ),
            )
        )

        relations = list(
            result.scalars().all(),
        )

        for relation in relations:

            # ====================================================================
            # RESOURCE = SOURCE
            # ====================================================================

            if relation.source_resource_id == resource.id:

                value = data.get(
                    relation.source_field_key,
                )

                if self._is_empty(value):
                    continue

                target_resource = await self._get_resource_or_fail(
                    resource_id=relation.target_resource_id,
                )

                target_records = await self._get_visible_records_for_relation(
                    resource=target_resource,
                    user_id=user_id,
                    is_admin=is_admin,
                )

                exists = any(
                    self._relation_values_equal(
                        target_record.data.get(
                            relation.target_field_key,
                        ),
                        value,
                    )
                    for target_record in target_records
                )

                if not exists:
                    raise ValueError(
                        f"La valeur « {value} » du champ "
                        f"« {relation.source_field_key} » "
                        f"n'existe pas dans la ressource "
                        f"« {target_resource.name} ».",
                    )

            # ====================================================================
            # RESOURCE = TARGET
            # ====================================================================

            if relation.target_resource_id == resource.id:

                value = data.get(
                    relation.target_field_key,
                )

                if self._is_empty(value):
                    continue

                existing_records = await self._get_visible_records_for_relation(
                    resource=resource,
                    user_id=user_id,
                    is_admin=is_admin,
                )

                for existing in existing_records:

                    if exclude_record_id is not None and existing.id == exclude_record_id:
                        continue

                    existing_value = (existing.data or {}).get(
                        relation.target_field_key,
                    )

                    if self._relation_values_equal(
                        existing_value,
                        value,
                    ):
                        raise ValueError(
                            f"La valeur « {value} » du champ "
                            f"« {relation.target_field_key} » "
                            "est déjà utilisée par une autre donnée. "
                            "Ce champ doit être unique car il est référencé "
                            "par une autre ressource.",
                        )

                if pending_records:

                    for pending in pending_records:

                        pending_value = pending.get(
                            relation.target_field_key,
                        )

                        if self._relation_values_equal(
                            pending_value,
                            value,
                        ):
                            raise ValueError(
                                f"La valeur « {value} » du champ "
                                f"« {relation.target_field_key} » "
                                "est dupliquée dans l'import.",
                            )

    # ========================================================================
    # RESOURCE CREATE
    # ========================================================================

    async def create(
        self,
        *,
        plugin_id: int,
        data: PluginResourceCreate,
    ) -> PluginResource:

        plugin = await self._get_plugin(
            plugin_id=plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        existing = await self.session.execute(
            select(PluginResource).where(
                PluginResource.plugin_id == plugin_id,
                PluginResource.key == data.key.strip(),
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError(
                "Une ressource avec cette clé existe déjà dans ce plugin.",
            )

        if data.scope == PluginResourceScope.GLOBAL and data.allow_user_schema_override:
            raise ValueError(
                "Une ressource GLOBAL ne peut pas autoriser " "la personnalisation utilisateur.",
            )

        self._validate_fields_collection(
            data.fields,
        )

        resource = PluginResource(
            plugin_id=plugin_id,
            key=data.key.strip(),
            name=data.name.strip(),
            description=data.description,
            scope=data.scope,
            allow_user_schema_override=(
                data.allow_user_schema_override if data.scope == PluginResourceScope.USER else False
            ),
            schema_definition={},
            position=data.position,
            icon=data.icon,
            is_active=data.is_active,
        )

        self.session.add(resource)

        await self.session.flush()

        for field_data in data.fields:
            self.session.add(
                self._build_field(
                    resource_id=resource.id,
                    data=field_data,
                )
            )

        await self.session.flush()

        await self._sync_schema_definition(
            resource.id,
        )

        return await self._reload(
            resource.id,
        )

    # ========================================================================
    # RESOURCE UPDATE
    # ========================================================================

    async def update(
        self,
        *,
        resource_id: int,
        data: PluginResourceUpdate,
    ) -> PluginResource:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        if data.scope == PluginResourceScope.GLOBAL:
            if data.allow_user_schema_override:
                raise ValueError(
                    "Une ressource GLOBAL ne peut pas autoriser "
                    "la personnalisation utilisateur.",
                )

            resource.allow_user_schema_override = False

        if data.name is not None:
            resource.name = data.name.strip()

        if data.description is not None:
            resource.description = data.description

        if data.scope is not None:
            resource.scope = data.scope

        if data.allow_user_schema_override is not None:

            if resource.scope == PluginResourceScope.GLOBAL and data.allow_user_schema_override:
                raise ValueError(
                    "Une ressource GLOBAL ne peut pas autoriser "
                    "la personnalisation utilisateur.",
                )

            resource.allow_user_schema_override = data.allow_user_schema_override

        if data.position is not None:
            resource.position = data.position

        if data.icon is not None:
            resource.icon = data.icon

        if data.is_active is not None:
            resource.is_active = data.is_active

        await self.session.flush()

        return await self._reload(
            resource.id,
        )

    # ========================================================================
    # RESOURCE DELETE
    # ========================================================================

    async def delete(
        self,
        *,
        resource_id: int,
    ) -> None:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        await self.session.delete(
            resource,
        )

        await self.session.flush()

    # ========================================================================
    # FIELD CREATE
    # ========================================================================

    async def add_field(
        self,
        *,
        resource_id: int,
        data: PluginResourceFieldCreate,
    ) -> PluginResource:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        self._validate_field(data)

        await self._ensure_field_key_available(
            resource_id=resource_id,
            key=data.key.strip(),
        )

        # ------------------------------------------------------------------------
        # Vérification de cohérence avec les données existantes
        # ------------------------------------------------------------------------

        records = await self._get_all_records(
            resource_id=resource_id,
        )

        if records and data.required and data.default_value is None:
            raise ValueError(
                f"Impossible d'ajouter le champ « {data.label} » comme "
                "obligatoire car la ressource contient déjà des données. "
                "Définissez une valeur par défaut ou rendez le champ facultatif."
            )

        # ------------------------------------------------------------------------
        # La valeur par défaut doit elle-même respecter le nouveau champ.
        # ------------------------------------------------------------------------

        if data.default_value is not None:
            self._validate_value(
                field=data.model_dump(mode="json"),
                value=data.default_value,
            )

        field = self._build_field(
            resource_id=resource_id,
            data=data,
        )

        self.session.add(field)

        await self.session.flush()

        await self._sync_schema_definition(
            resource_id,
        )

        new_field = self._field_to_dict(field)

        # ------------------------------------------------------------------------
        # Migration des données existantes
        # ------------------------------------------------------------------------

        if records:
            for record in records:
                migrated_data = dict(record.data or {})

                if data.default_value is not None:
                    migrated_data[data.key.strip()] = data.default_value
                else:
                    migrated_data[data.key.strip()] = None

                # Validation finale avec le nouveau schema.
                self.validate_record(
                    schema=self._resource_schema(resource),
                    data=migrated_data,
                )

                record.data = migrated_data

            await self.session.flush()

        # ------------------------------------------------------------------------
        # Propagation vers les overrides USER
        # ------------------------------------------------------------------------

        if resource.scope == PluginResourceScope.USER:
            await self._propagate_admin_field_addition(
                resource_id=resource_id,
                field=new_field,
            )

        return await self._reload(
            resource.id,
        )

    # ========================================================================
    # FIELD UPDATE
    # ========================================================================

    async def update_field(
        self,
        *,
        resource_id: int,
        field_id: int,
        data: PluginResourceFieldUpdate,
    ) -> PluginResource:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        result = await self.session.execute(
            select(PluginResourceField).where(
                PluginResourceField.id == field_id,
                PluginResourceField.resource_id == resource_id,
            )
        )

        field = result.scalar_one_or_none()

        if field is None:
            raise ValueError(
                "Champ introuvable.",
            )

        self._validate_partial_field(data)

        # ------------------------------------------------------------------------
        # Construire une copie prospective du champ.
        # On ne modifie PAS encore SQLAlchemy.
        # ------------------------------------------------------------------------

        prospective = self._field_to_dict(field)

        if data.key is not None:
            prospective["key"] = data.key.strip()

        if data.label is not None:
            prospective["label"] = data.label.strip()

        if data.description is not None:
            prospective["description"] = data.description

        if data.field_type is not None:
            prospective["field_type"] = (
                data.field_type.value if hasattr(data.field_type, "value") else data.field_type
            )

        if data.required is not None:
            prospective["required"] = data.required

        if "min_length" in data.model_fields_set:
            prospective["min_length"] = data.min_length

        if "max_length" in data.model_fields_set:
            prospective["max_length"] = data.max_length

        if "min_value" in data.model_fields_set:
            prospective["min_value"] = data.min_value

        if "max_value" in data.model_fields_set:
            prospective["max_value"] = data.max_value

        if "pattern" in data.model_fields_set:
            prospective["pattern"] = data.pattern

        if data.options is not None:
            prospective["options"] = data.options

        if "default_value" in data.model_fields_set:
            prospective["default_value"] = data.default_value

        if data.position is not None:
            prospective["position"] = data.position

        if data.is_active is not None:
            prospective["is_active"] = data.is_active

        # ------------------------------------------------------------------------
        # Validation complète du champ prospectif.
        # ------------------------------------------------------------------------

        prospective_model = PluginResourceFieldCreate(
            **prospective,
        )

        self._validate_field(
            prospective_model,
        )

        old_key = field.key
        new_key = prospective["key"]

        if new_key != old_key:
            await self._ensure_field_key_available(
                resource_id=resource_id,
                key=new_key,
                exclude_field_id=field_id,
            )

        # ------------------------------------------------------------------------
        # Récupérer les données existantes.
        # ------------------------------------------------------------------------

        records = await self._get_all_records(
            resource_id=resource_id,
        )

        # ------------------------------------------------------------------------
        # Construire le schema prospectif.
        # ------------------------------------------------------------------------

        current_fields = [
            self._field_to_dict(existing) for existing in resource.fields if existing.id != field.id
        ]

        current_fields.append(
            prospective,
        )

        current_fields.sort(
            key=lambda item: item.get(
                "position",
                0,
            )
        )

        prospective_schema = {
            "version": 1,
            "fields": current_fields,
        }

        # ------------------------------------------------------------------------
        # Migration des données.
        # ------------------------------------------------------------------------

        migration_map: dict[str, tuple[str, Any]] = {}

        if old_key != new_key:
            migration_map[old_key] = (
                new_key,
                prospective.get("default_value"),
            )

        migrated_data: list[dict[str, Any]] = []

        for record in records:

            current = dict(record.data or {})

            # Renommage.
            if old_key != new_key and old_key in current:
                current[new_key] = current.pop(old_key)

            # Nouveau champ obligatoire sans valeur existante.
            value_exists = new_key in current and not self._is_empty(
                current[new_key],
            )

            if not value_exists:

                if prospective.get("required", False):

                    if prospective.get("default_value") is None:
                        raise ValueError(
                            f"Impossible de rendre le champ "
                            f"« {prospective['label']} » obligatoire : "
                            "certaines données existantes n'ont pas de valeur "
                            "pour ce champ. Définissez une valeur par défaut."
                        )

                    current[new_key] = prospective["default_value"]

                elif new_key not in current:
                    current[new_key] = None

            # Validation stricte de la donnée avec le nouveau schema.
            self.validate_record(
                schema=prospective_schema,
                data=current,
            )

            migrated_data.append(current)

        # ------------------------------------------------------------------------
        # Appliquer maintenant la modification.
        # ------------------------------------------------------------------------

        field.key = prospective["key"]
        field.label = prospective["label"]
        field.description = prospective["description"]
        field.field_type = (
            prospective["field_type"]
            if isinstance(prospective["field_type"], PluginFieldType)
            else PluginFieldType(prospective["field_type"])
        )
        field.required = prospective["required"]
        field.min_length = prospective["min_length"]
        field.max_length = prospective["max_length"]
        field.min_value = prospective["min_value"]
        field.max_value = prospective["max_value"]
        field.pattern = prospective["pattern"]
        field.options = prospective["options"]
        field.default_value = prospective["default_value"]
        field.position = prospective["position"]
        field.is_active = prospective["is_active"]

        await self.session.flush()

        await self._sync_schema_definition(
            resource_id,
        )

        if records:
            await self._apply_record_data_migration(
                records=records,
                migrated_data=migrated_data,
            )

        # ------------------------------------------------------------------------
        # Propager la modification admin aux overrides USER.
        # ------------------------------------------------------------------------

        if resource.scope == PluginResourceScope.USER:
            await self._propagate_admin_field_update(
                resource_id=resource_id,
                old_key=old_key,
                field=self._field_to_dict(field),
            )

        return await self._reload(
            resource_id,
        )

    # ========================================================================
    # FIELD DELETE
    # ========================================================================

    async def delete_field(
        self,
        *,
        resource_id: int,
        field_id: int,
    ) -> PluginResource:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        result = await self.session.execute(
            select(PluginResourceField).where(
                PluginResourceField.id == field_id,
                PluginResourceField.resource_id == resource_id,
            )
        )

        field = result.scalar_one_or_none()

        if field is None:
            raise ValueError(
                "Champ introuvable.",
            )

        field_key = field.key

        records = await self._get_all_records(
            resource_id=resource_id,
        )

        # ------------------------------------------------------------------------
        # Construire le schema après suppression.
        # ------------------------------------------------------------------------

        remaining_fields = [
            self._field_to_dict(existing) for existing in resource.fields if existing.id != field_id
        ]

        remaining_fields.sort(
            key=lambda item: item.get(
                "position",
                0,
            )
        )

        prospective_schema = {
            "version": 1,
            "fields": remaining_fields,
        }

        migrated_data: list[dict[str, Any]] = []

        for record in records:

            current = dict(record.data or {})

            current.pop(
                field_key,
                None,
            )

            self.validate_record(
                schema=prospective_schema,
                data=current,
            )

            migrated_data.append(current)

        # ------------------------------------------------------------------------
        # Suppression.
        # ------------------------------------------------------------------------

        await self.session.delete(
            field,
        )

        await self.session.flush()

        await self._sync_schema_definition(
            resource_id,
        )

        if records:
            await self._apply_record_data_migration(
                records=records,
                migrated_data=migrated_data,
            )

        if resource.scope == PluginResourceScope.USER:
            await self._propagate_admin_field_delete(
                resource_id=resource_id,
                field_key=field_key,
            )

        return await self._reload(
            resource_id,
        )

    # ========================================================================
    # RECORD LIST
    # ========================================================================

    async def list_records(
        self,
        *,
        resource_id: int,
        user_id: int,
        is_admin: bool,
    ) -> list[PluginResourceRecord]:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        if resource.scope == PluginResourceScope.GLOBAL:

            result = await self.session.execute(
                select(PluginResourceRecord)
                .where(
                    PluginResourceRecord.resource_id == resource_id,
                    PluginResourceRecord.user_id.is_(None),
                )
                .order_by(
                    PluginResourceRecord.created_at.desc(),
                )
            )

            return list(
                result.scalars().all(),
            )

        # USER RESOURCE
        #
        # Admin sees:
        #   - shared admin records
        #   - all user records
        #
        # User sees:
        #   - shared admin records
        #   - his own records

        if is_admin:

            result = await self.session.execute(
                select(PluginResourceRecord)
                .where(
                    PluginResourceRecord.resource_id == resource_id,
                )
                .order_by(
                    PluginResourceRecord.created_at.desc(),
                )
            )

        else:

            result = await self.session.execute(
                select(PluginResourceRecord)
                .where(
                    PluginResourceRecord.resource_id == resource_id,
                    or_(
                        PluginResourceRecord.user_id.is_(None),
                        PluginResourceRecord.user_id == user_id,
                    ),
                )
                .order_by(
                    PluginResourceRecord.created_at.desc(),
                )
            )

        return list(
            result.scalars().all(),
        )

    # ========================================================================
    # RECORD CREATE
    # ========================================================================

    async def create_record(
        self,
        *,
        resource_id: int,
        data: PluginResourceRecordCreate,
        user_id: int,
        is_admin: bool,
    ) -> PluginResourceRecord:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        if not resource.fields:
            raise ValueError(
                "Impossible d'ajouter une donnée : " "la ressource ne possède encore aucun champ."
            )

        owner_id: int | None

        if resource.scope == PluginResourceScope.GLOBAL:

            if not is_admin:
                raise ValueError(
                    "Seul un administrateur peut créer une donnée GLOBAL.",
                )

            owner_id = None

            schema = self._resource_schema(
                resource,
            )

        else:

            if is_admin:
                # Donnée admin commune à tous.
                owner_id = None

                schema = self._resource_schema(
                    resource,
                )

            else:
                # Donnée propre à l'utilisateur.
                owner_id = user_id

                schema = await self.get_effective_schema(
                    resource_id=resource_id,
                    user_id=user_id,
                )

        normalized = self.validate_record(
            schema=schema,
            data=data.data,
        )

        await self._validate_record_relations(
            resource=resource,
            data=normalized,
            user_id=user_id,
            owner_id=owner_id,
            is_admin=is_admin,
        )

        record = PluginResourceRecord(
            resource_id=resource_id,
            user_id=owner_id,
            data=normalized,
            is_active=data.is_active,
        )

        self.session.add(
            record,
        )

        await self.session.flush()

        return record

    # ========================================================================
    # RECORD UPDATE
    # ========================================================================

    async def update_record(
        self,
        *,
        resource_id: int,
        record_id: int,
        data: PluginResourceRecordUpdate,
        user_id: int,
        is_admin: bool,
    ) -> PluginResourceRecord:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        result = await self.session.execute(
            select(PluginResourceRecord).where(
                PluginResourceRecord.id == record_id,
                PluginResourceRecord.resource_id == resource_id,
            )
        )

        record = result.scalar_one_or_none()

        if record is None:
            raise ValueError(
                "Donnée introuvable.",
            )

        # GLOBAL
        if resource.scope == PluginResourceScope.GLOBAL:

            if not is_admin:
                raise ValueError(
                    "Seul un administrateur peut modifier " "une donnée GLOBAL.",
                )

            schema = self._resource_schema(
                resource,
            )

        # USER
        else:

            # Admin-owned shared record.
            if record.user_id is None:

                if not is_admin:
                    raise ValueError(
                        "Cette donnée commune est administrée " "uniquement par un administrateur.",
                    )

                schema = self._resource_schema(
                    resource,
                )

            # User-owned record.
            else:

                if not is_admin and record.user_id != user_id:
                    raise ValueError(
                        "Vous ne pouvez pas modifier " "la donnée d'un autre utilisateur.",
                    )

                schema = await self.get_effective_schema(
                    resource_id=resource_id,
                    user_id=record.user_id,
                )

        if not schema.get("fields"):
            raise ValueError(
                "Impossible de modifier une donnée : " "la ressource ne possède aucun champ."
            )

        if data.data is not None:
            record.data = self.validate_record(
                schema=schema,
                data=data.data,
            )

            normalized = self.validate_record(
                schema=schema,
                data=data.data,
            )

            await self._validate_record_relations(
                resource=resource,
                data=normalized,
                user_id=user_id,
                owner_id=record.user_id,
                is_admin=is_admin,
                exclude_record_id=record.id,
            )

            record.data = normalized

        if data.is_active is not None:
            record.is_active = data.is_active

        await self.session.flush()

        return record

    # ========================================================================
    # RECORD DELETE
    # ========================================================================

    async def delete_record(
        self,
        *,
        resource_id: int,
        record_id: int,
        user_id: int,
        is_admin: bool,
    ) -> None:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        result = await self.session.execute(
            select(PluginResourceRecord).where(
                PluginResourceRecord.id == record_id,
                PluginResourceRecord.resource_id == resource_id,
            )
        )

        record = result.scalar_one_or_none()

        if record is None:
            raise ValueError(
                "Donnée introuvable.",
            )

        if resource.scope == PluginResourceScope.GLOBAL:

            if not is_admin:
                raise ValueError(
                    "Seul un administrateur peut supprimer " "une donnée GLOBAL.",
                )

        else:

            if record.user_id is None:

                if not is_admin:
                    raise ValueError(
                        "Cette donnée commune est administrée " "uniquement par un administrateur.",
                    )

            elif not is_admin and record.user_id != user_id:

                raise ValueError(
                    "Vous ne pouvez pas supprimer " "la donnée d'un autre utilisateur.",
                )

        await self.session.delete(
            record,
        )

        await self.session.flush()

    # ========================================================================
    # EFFECTIVE SCHEMA
    # ========================================================================

    async def get_effective_schema(
        self,
        *,
        resource_id: int,
        user_id: int | None,
    ) -> dict[str, Any]:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        base_schema = self._resource_schema(
            resource,
        )

        if (
            resource.scope != PluginResourceScope.USER
            or not resource.allow_user_schema_override
            or user_id is None
        ):
            return base_schema

        result = await self.session.execute(
            select(PluginResourceUserSchema).where(
                PluginResourceUserSchema.resource_id == resource_id,
                PluginResourceUserSchema.user_id == user_id,
            )
        )

        override = result.scalar_one_or_none()

        if override is None:
            return base_schema

        return override.schema_definition

    async def get_effective_schema_payload(
        self,
        *,
        resource_id: int,
        user_id: int,
    ) -> dict[str, Any]:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        schema = await self.get_effective_schema(
            resource_id=resource_id,
            user_id=user_id,
        )

        overridden = False

        if resource.scope == PluginResourceScope.USER and resource.allow_user_schema_override:
            result = await self.session.execute(
                select(PluginResourceUserSchema).where(
                    PluginResourceUserSchema.resource_id == resource_id,
                    PluginResourceUserSchema.user_id == user_id,
                )
            )

            overridden = result.scalar_one_or_none() is not None

        return {
            "resource_id": resource.id,
            "scope": resource.scope,
            "allow_user_schema_override": (resource.allow_user_schema_override),
            "is_overridden": overridden,
            "schema_definition": schema,
            "fields": schema.get(
                "fields",
                [],
            ),
        }

    # ========================================================================
    # USER SCHEMA OVERRIDE
    # ========================================================================

    async def update_user_schema(
        self,
        *,
        resource_id: int,
        user_id: int,
        data: PluginResourceUserSchemaUpdate,
    ) -> PluginResourceUserSchema:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        if resource.scope != PluginResourceScope.USER:
            raise ValueError(
                "Seules les ressources USER peuvent " "avoir un schema personnalisé.",
            )

        if not resource.allow_user_schema_override:
            raise ValueError(
                "La personnalisation du schema est désactivée " "par l'administrateur.",
            )

        self._validate_fields_collection(
            data.fields,
        )

        schema = self._build_schema_from_fields(
            data.fields,
        )

        # ------------------------------------------------------------------------
        # Vérifier la cohérence avec les données appartenant à cet utilisateur.
        # ------------------------------------------------------------------------

        records_result = await self.session.execute(
            select(PluginResourceRecord).where(
                PluginResourceRecord.resource_id == resource_id,
                PluginResourceRecord.user_id == user_id,
            )
        )

        records = list(
            records_result.scalars().all(),
        )

        if not schema.get("fields"):
            if records:
                raise ValueError(
                    "Impossible de supprimer tous les champs du schema "
                    "car cet utilisateur possède déjà des données."
                )

        migrated_data: list[dict[str, Any]] = []

        for record in records:

            current = dict(record.data or {})

            normalized = self.validate_record(
                schema=schema,
                data=current,
            )

            migrated_data.append(normalized)

        # ------------------------------------------------------------------------
        # Upsert du schema.
        # ------------------------------------------------------------------------

        result = await self.session.execute(
            select(PluginResourceUserSchema).where(
                PluginResourceUserSchema.resource_id == resource_id,
                PluginResourceUserSchema.user_id == user_id,
            )
        )

        override = result.scalar_one_or_none()

        if override is None:

            override = PluginResourceUserSchema(
                resource_id=resource_id,
                user_id=user_id,
                schema_definition=schema,
            )

            self.session.add(
                override,
            )

        else:

            override.schema_definition = schema

        await self.session.flush()

        # ------------------------------------------------------------------------
        # Mettre à jour les données si nécessaire.
        # ------------------------------------------------------------------------

        if records:
            for record, migrated in zip(
                records,
                migrated_data,
                strict=True,
            ):
                record.data = migrated

            await self.session.flush()

        # ------------------------------------------------------------------------
        # IMPORTANT :
        # server_onupdate peut rendre updated_at expiré après flush.
        # On recharge explicitement l'objet avant Pydantic.
        # ------------------------------------------------------------------------

        await self.session.refresh(
            override,
        )

        return override

    async def reset_user_schema(
        self,
        *,
        resource_id: int,
        user_id: int,
    ) -> None:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        if resource.scope != PluginResourceScope.USER:
            raise ValueError(
                "Seules les ressources USER peuvent " "avoir un schema personnalisé.",
            )

        await self.session.execute(
            delete(PluginResourceUserSchema).where(
                PluginResourceUserSchema.resource_id == resource_id,
                PluginResourceUserSchema.user_id == user_id,
            )
        )

        await self.session.flush()

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @classmethod
    def validate_record(
        cls,
        *,
        schema: dict[str, Any],
        data: dict[str, Any],
    ) -> dict[str, Any]:

        fields = schema.get(
            "fields",
            [],
        )

        if not isinstance(fields, list):
            raise ValueError(
                "Schema de ressource invalide.",
            )

        active_fields = [
            field
            for field in fields
            if field.get(
                "is_active",
                True,
            )
        ]

        field_map = {field["key"]: field for field in active_fields}

        unknown = set(data.keys()) - set(field_map.keys())

        if unknown:
            raise ValueError(
                "Champs inconnus : "
                + ", ".join(
                    sorted(unknown),
                ),
            )

        normalized: dict[str, Any] = {}

        for field in active_fields:

            key = field["key"]

            value = data.get(
                key,
            )

            if cls._is_empty(
                value,
            ):

                if field.get(
                    "required",
                    False,
                ):
                    raise ValueError(
                        f"Le champ « {field.get('label', key)} » " "est obligatoire.",
                    )

                if "default_value" in field and field["default_value"] is not None:
                    normalized[key] = field["default_value"]

                continue

            normalized[key] = cls._validate_value(
                field=field,
                value=value,
            )

        return normalized

    @classmethod
    def _validate_value(
        cls,
        *,
        field: dict[str, Any],
        value: Any,
    ) -> Any:

        field_type = field.get(
            "field_type",
        )

        if field_type is not None and hasattr(
            field_type,
            "value",
        ):
            field_type = field_type.value

        # --------------------------------------------------------------------
        # TEXT
        # --------------------------------------------------------------------

        if field_type in {
            "TEXT",
            "LONG_TEXT",
        }:

            if not isinstance(
                value,
                str,
            ):
                value = str(value)

            value = value.strip()

            min_length = field.get(
                "min_length",
            )

            max_length = field.get(
                "max_length",
            )

            if min_length is not None and len(value) < min_length:
                raise ValueError(
                    f"Minimum {min_length} caractères.",
                )

            if max_length is not None and len(value) > max_length:
                raise ValueError(
                    f"Maximum {max_length} caractères.",
                )

            pattern = field.get(
                "pattern",
            )

            if pattern:

                try:
                    matches = re.fullmatch(
                        pattern,
                        value,
                    )
                except re.error as exc:
                    raise ValueError(
                        "Le pattern du champ est invalide.",
                    ) from exc

                if not matches:
                    raise ValueError(
                        "La valeur ne respecte pas " "le format demandé.",
                    )

            return value

        # --------------------------------------------------------------------
        # NUMBER
        # --------------------------------------------------------------------

        if field_type == "NUMBER":

            if isinstance(
                value,
                bool,
            ):
                raise ValueError(
                    "La valeur doit être un nombre entier.",
                )

            try:
                number = float(
                    value,
                )
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise ValueError(
                    "La valeur doit être numérique.",
                ) from exc

            if not number.is_integer():
                raise ValueError(
                    "La valeur doit être un entier.",
                )

            number = int(
                number,
            )

            cls._validate_numeric_bounds(
                field=field,
                value=number,
            )

            return number

        # --------------------------------------------------------------------
        # DECIMAL
        # --------------------------------------------------------------------

        if field_type == "DECIMAL":

            if isinstance(
                value,
                bool,
            ):
                raise ValueError(
                    "La valeur doit être numérique.",
                )

            try:
                number = float(
                    value,
                )
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise ValueError(
                    "La valeur doit être numérique.",
                ) from exc

            cls._validate_numeric_bounds(
                field=field,
                value=number,
            )

            return number

        # --------------------------------------------------------------------
        # BOOLEAN
        # --------------------------------------------------------------------

        if field_type == "BOOLEAN":

            if isinstance(
                value,
                bool,
            ):
                return value

            normalized = (
                str(
                    value,
                )
                .strip()
                .lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
                "oui",
                "vrai",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "non",
                "faux",
            }:
                return False

            raise ValueError(
                "La valeur doit être booléenne.",
            )

        # --------------------------------------------------------------------
        # EMAIL
        # --------------------------------------------------------------------

        if field_type == "EMAIL":

            value = str(
                value,
            ).strip()

            if not re.fullmatch(
                r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                value,
            ):
                raise ValueError(
                    "Adresse email invalide.",
                )

            return value

        # --------------------------------------------------------------------
        # PHONE
        # --------------------------------------------------------------------

        if field_type == "PHONE":

            value = str(
                value,
            ).strip()

            if not re.fullmatch(
                r"^\+?[0-9][0-9\s().-]{5,}$",
                value,
            ):
                raise ValueError(
                    "Numéro de téléphone invalide.",
                )

            return value

        # --------------------------------------------------------------------
        # COUNTRY
        # --------------------------------------------------------------------

        if field_type == "COUNTRY":

            value = (
                str(
                    value,
                )
                .strip()
                .upper()
            )

            if not re.fullmatch(
                r"[A-Z]{2}",
                value,
            ):
                raise ValueError(
                    "Le pays doit être un code ISO alpha-2.",
                )

            return value

        # --------------------------------------------------------------------
        # URL
        # --------------------------------------------------------------------

        if field_type == "URL":

            value = str(
                value,
            ).strip()

            if not re.fullmatch(
                r"^https?://.+$",
                value,
                flags=re.IGNORECASE,
            ):
                raise ValueError(
                    "URL invalide.",
                )

            return value

        # --------------------------------------------------------------------
        # DATE
        # --------------------------------------------------------------------

        if field_type == "DATE":

            if isinstance(
                value,
                datetime,
            ):
                return value.date().isoformat()

            if isinstance(
                value,
                date,
            ):
                return value.isoformat()

            try:
                return date.fromisoformat(
                    str(value).strip(),
                ).isoformat()
            except ValueError as exc:
                raise ValueError(
                    "Date invalide. Format attendu : YYYY-MM-DD.",
                ) from exc

        # --------------------------------------------------------------------
        # DATETIME
        # --------------------------------------------------------------------

        if field_type == "DATETIME":

            if isinstance(
                value,
                datetime,
            ):
                return value.isoformat()

            try:
                return datetime.fromisoformat(
                    str(value).strip(),
                ).isoformat()
            except ValueError as exc:
                raise ValueError(
                    "Date/heure invalide.",
                ) from exc

        # --------------------------------------------------------------------
        # SINGLE CHOICE
        # --------------------------------------------------------------------

        if field_type == "SINGLE_CHOICE":

            options = field.get(
                "options",
                [],
            )

            allowed = cls._choice_values(
                options,
            )

            if value not in allowed:
                raise ValueError(
                    "La valeur ne fait pas partie " "des options autorisées.",
                )

            return value

        # --------------------------------------------------------------------
        # MULTIPLE CHOICE
        # --------------------------------------------------------------------

        if field_type == "MULTIPLE_CHOICE":

            if isinstance(
                value,
                str,
            ):
                value = [item.strip() for item in value.split(",") if item.strip()]

            if not isinstance(
                value,
                list,
            ):
                raise ValueError(
                    "Une sélection multiple doit être une liste.",
                )

            allowed = cls._choice_values(
                field.get(
                    "options",
                    [],
                ),
            )

            invalid = [item for item in value if item not in allowed]

            if invalid:
                raise ValueError(
                    "Certaines valeurs ne font pas partie " "des options autorisées.",
                )

            return value

        return value

    @staticmethod
    def _choice_values(
        options: list[Any],
    ) -> list[Any]:

        values: list[Any] = []

        for option in options:

            if isinstance(
                option,
                dict,
            ):
                if "value" in option:
                    values.append(
                        option["value"],
                    )

            else:
                values.append(
                    option,
                )

        return values

    @staticmethod
    def _validate_numeric_bounds(
        *,
        field: dict[str, Any],
        value: float | int,
    ) -> None:

        min_value = field.get(
            "min_value",
        )

        max_value = field.get(
            "max_value",
        )

        if min_value is not None and value < min_value:
            raise ValueError(
                f"La valeur minimale est {min_value}.",
            )

        if max_value is not None and value > max_value:
            raise ValueError(
                f"La valeur maximale est {max_value}.",
            )

    # ========================================================================
    # SCHEMA HELPERS
    # ========================================================================

    @classmethod
    def _resource_schema(
        cls,
        resource: PluginResource,
    ) -> dict[str, Any]:

        fields = sorted(
            resource.fields,
            key=lambda item: item.position,
        )

        return {
            "version": 1,
            "fields": [
                cls._field_to_dict(
                    field,
                )
                for field in fields
            ],
        }

    @classmethod
    def _build_schema_from_fields(
        cls,
        fields: list[Any],
    ) -> dict[str, Any]:

        serialized = []

        for field in fields:

            if isinstance(
                field,
                PluginResourceField,
            ):
                serialized.append(
                    cls._field_to_dict(
                        field,
                    )
                )
            elif hasattr(
                field,
                "model_dump",
            ):
                serialized.append(
                    field.model_dump(
                        mode="json",
                    )
                )
            else:
                serialized.append(
                    dict(field),
                )

        serialized.sort(
            key=lambda item: item.get(
                "position",
                0,
            )
        )

        return {
            "version": 1,
            "fields": serialized,
        }

    @staticmethod
    def _field_to_dict(
        field: PluginResourceField,
    ) -> dict[str, Any]:

        field_type = field.field_type

        if hasattr(
            field_type,
            "value",
        ):
            field_type = field_type.value

        return {
            "key": field.key,
            "label": field.label,
            "description": field.description,
            "field_type": field_type,
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

    @staticmethod
    def _build_field(
        *,
        resource_id: int,
        data: PluginResourceFieldCreate,
    ) -> PluginResourceField:

        return PluginResourceField(
            resource_id=resource_id,
            key=data.key.strip(),
            label=data.label.strip(),
            description=data.description,
            field_type=data.field_type,
            required=data.required,
            min_length=data.min_length,
            max_length=data.max_length,
            min_value=data.min_value,
            max_value=data.max_value,
            pattern=data.pattern,
            options=data.options,
            default_value=data.default_value,
            position=data.position,
            is_active=data.is_active,
        )

    # ========================================================================
    # VALIDATION HELPERS
    # ========================================================================

    @classmethod
    def _validate_fields_collection(
        cls,
        fields: list[PluginResourceFieldCreate],
    ) -> None:

        keys: set[str] = set()

        for field in fields:

            cls._validate_field(
                field,
            )

            key = field.key.strip()

            if key in keys:
                raise ValueError(
                    f"La clé de champ « {key} » est dupliquée.",
                )

            keys.add(key)

    @staticmethod
    def _validate_field(
        field: PluginResourceFieldCreate,
    ) -> None:

        if (
            field.min_length is not None
            and field.max_length is not None
            and field.min_length > field.max_length
        ):
            raise ValueError(
                "min_length ne peut pas être supérieur à max_length.",
            )

        if (
            field.min_value is not None
            and field.max_value is not None
            and field.min_value > field.max_value
        ):
            raise ValueError(
                "min_value ne peut pas être supérieur à max_value.",
            )

        if field.field_type in {
            PluginFieldType.SINGLE_CHOICE,
            PluginFieldType.MULTIPLE_CHOICE,
        }:

            if not field.options:
                raise ValueError(
                    "Un champ de type choix doit posséder " "au moins une option.",
                )

        if field.pattern:

            try:
                re.compile(
                    field.pattern,
                )
            except re.error as exc:
                raise ValueError(
                    f"Pattern invalide pour le champ « {field.key} ».",
                ) from exc

    @staticmethod
    def _validate_partial_field(
        field: PluginResourceFieldUpdate,
    ) -> None:

        if (
            field.min_length is not None
            and field.max_length is not None
            and field.min_length > field.max_length
        ):
            raise ValueError(
                "min_length ne peut pas être supérieur à max_length.",
            )

        if (
            field.min_value is not None
            and field.max_value is not None
            and field.min_value > field.max_value
        ):
            raise ValueError(
                "min_value ne peut pas être supérieur à max_value.",
            )

        if field.pattern:

            try:
                re.compile(
                    field.pattern,
                )
            except re.error as exc:
                raise ValueError(
                    "Pattern invalide.",
                ) from exc

    @staticmethod
    def _validate_model_field_values(
        field: PluginResourceField,
    ) -> None:

        if (
            field.min_length is not None
            and field.max_length is not None
            and field.min_length > field.max_length
        ):
            raise ValueError(
                "min_length ne peut pas être supérieur à max_length.",
            )

        if (
            field.min_value is not None
            and field.max_value is not None
            and field.min_value > field.max_value
        ):
            raise ValueError(
                "min_value ne peut pas être supérieur à max_value.",
            )

        if field.pattern:

            try:
                re.compile(
                    field.pattern,
                )
            except re.error as exc:
                raise ValueError(
                    "Pattern invalide.",
                ) from exc

    async def _ensure_field_key_available(
        self,
        *,
        resource_id: int,
        key: str,
        exclude_field_id: int | None = None,
    ) -> None:

        query = select(
            PluginResourceField,
        ).where(
            PluginResourceField.resource_id == resource_id,
            PluginResourceField.key == key,
        )

        if exclude_field_id is not None:

            query = query.where(
                PluginResourceField.id != exclude_field_id,
            )

        result = await self.session.execute(
            query,
        )

        if result.scalar_one_or_none() is not None:
            raise ValueError(
                f"Un champ avec la clé « {key} » existe déjà.",
            )

    # ============================================================================
    # SCHEMA / RECORD CONSISTENCY
    # ============================================================================

    async def _get_all_records(
        self,
        *,
        resource_id: int,
    ) -> list[PluginResourceRecord]:

        result = await self.session.execute(
            select(PluginResourceRecord)
            .where(
                PluginResourceRecord.resource_id == resource_id,
            )
            .order_by(
                PluginResourceRecord.id.asc(),
            )
        )

        return list(result.scalars().all())

    @staticmethod
    def _field_has_default(
        field: dict[str, Any],
    ) -> bool:

        return "default_value" in field and field["default_value"] is not None

    @classmethod
    def _validate_existing_records_against_schema(
        cls,
        *,
        records: list[PluginResourceRecord],
        schema: dict[str, Any],
        field_migrations: dict[str, tuple[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:

        field_migrations = field_migrations or {}

        migrated_records: list[dict[str, Any]] = []

        for record in records:
            current = dict(record.data or {})

            for old_key, migration in field_migrations.items():
                new_key, default_value = migration

                if old_key == new_key:
                    continue

                if old_key in current:
                    current[new_key] = current.pop(old_key)
                elif new_key not in current and default_value is not None:
                    current[new_key] = default_value

            normalized = cls.validate_record(
                schema=schema,
                data=current,
            )

            # Conserver explicitement les champs facultatifs absents
            # comme null lorsqu'une migration l'exige.
            for field in schema.get("fields", []):
                key = field["key"]

                if key not in current and not field.get("required", False):
                    current[key] = None

            migrated_records.append(current)

        return migrated_records

    async def _apply_record_data_migration(
        self,
        *,
        records: list[PluginResourceRecord],
        migrated_data: list[dict[str, Any]],
    ) -> None:

        if len(records) != len(migrated_data):
            raise ValueError(
                "Erreur interne pendant la migration des données.",
            )

        for record, data in zip(
            records,
            migrated_data,
            strict=True,
        ):
            record.data = data

        await self.session.flush()

    async def _get_user_schema_overrides(
        self,
        *,
        resource_id: int,
    ) -> list[PluginResourceUserSchema]:

        result = await self.session.execute(
            select(PluginResourceUserSchema).where(
                PluginResourceUserSchema.resource_id == resource_id,
            )
        )

        return list(result.scalars().all())

    async def _propagate_admin_field_addition(
        self,
        *,
        resource_id: int,
        field: dict[str, Any],
    ) -> None:

        overrides = await self._get_user_schema_overrides(
            resource_id=resource_id,
        )

        if not overrides:
            return

        for override in overrides:

            schema = dict(
                override.schema_definition or {},
            )

            fields = list(
                schema.get(
                    "fields",
                    [],
                )
            )

            if any(existing.get("key") == field["key"] for existing in fields):
                continue

            fields.append(dict(field))

            fields.sort(
                key=lambda item: item.get(
                    "position",
                    0,
                )
            )

            override.schema_definition = {
                "version": 1,
                "fields": fields,
            }

        await self.session.flush()

    async def _propagate_admin_field_update(
        self,
        *,
        resource_id: int,
        old_key: str,
        field: dict[str, Any],
    ) -> None:

        overrides = await self._get_user_schema_overrides(
            resource_id=resource_id,
        )

        if not overrides:
            return

        for override in overrides:

            schema = dict(
                override.schema_definition or {},
            )

            fields = list(
                schema.get(
                    "fields",
                    [],
                )
            )

            found = False

            for index, existing in enumerate(fields):

                if existing.get("key") == old_key:
                    fields[index] = dict(field)
                    found = True
                    break

            if not found:
                fields.append(dict(field))

            fields.sort(
                key=lambda item: item.get(
                    "position",
                    0,
                )
            )

            override.schema_definition = {
                "version": 1,
                "fields": fields,
            }

        await self.session.flush()

    async def _propagate_admin_field_delete(
        self,
        *,
        resource_id: int,
        field_key: str,
    ) -> None:

        overrides = await self._get_user_schema_overrides(
            resource_id=resource_id,
        )

        if not overrides:
            return

        for override in overrides:

            schema = dict(
                override.schema_definition or {},
            )

            fields = [
                field
                for field in schema.get(
                    "fields",
                    [],
                )
                if field.get("key") != field_key
            ]

            override.schema_definition = {
                "version": 1,
                "fields": fields,
            }

        await self.session.flush()

    # ============================================================================
    # RESOURCE RELATIONS
    # ============================================================================

    async def list_relations(
        self,
        *,
        resource_id: int,
    ) -> list[PluginResourceRelation]:

        await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        result = await self.session.execute(
            select(PluginResourceRelation)
            .options(
                selectinload(
                    PluginResourceRelation.source_resource,
                ),
                selectinload(
                    PluginResourceRelation.target_resource,
                ),
            )
            .where(
                or_(
                    PluginResourceRelation.source_resource_id == resource_id,
                    PluginResourceRelation.target_resource_id == resource_id,
                )
            )
            .order_by(
                PluginResourceRelation.created_at.asc(),
            )
        )

        return list(result.scalars().all())

    async def create_relation(
        self,
        *,
        resource_id: int,
        data: PluginResourceRelationCreate,
    ) -> PluginResourceRelation:

        source_resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=source_resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        target_resource = await self._get_resource_or_fail(
            resource_id=data.target_resource_id,
        )

        if source_resource.plugin_id != target_resource.plugin_id:
            raise ValueError(
                "Une ressource ne peut être liée qu'à une autre ressource " "du même plugin.",
            )

        if source_resource.id == target_resource.id:
            raise ValueError(
                "Une ressource ne peut pas être liée à elle-même.",
            )

        source_field = next(
            (
                field
                for field in source_resource.fields
                if field.key == data.source_field_key and field.is_active
            ),
            None,
        )

        if source_field is None:
            raise ValueError(
                f"Le champ source « {data.source_field_key} » " "n'existe pas dans la ressource.",
            )

        target_field = next(
            (
                field
                for field in target_resource.fields
                if field.key == data.target_field_key and field.is_active
            ),
            None,
        )

        if target_field is None:
            raise ValueError(
                f"Le champ cible « {data.target_field_key} » "
                "n'existe pas dans la ressource cible.",
            )

        source_type = (
            source_field.field_type.value
            if hasattr(source_field.field_type, "value")
            else source_field.field_type
        )

        target_type = (
            target_field.field_type.value
            if hasattr(target_field.field_type, "value")
            else target_field.field_type
        )

        if source_type != target_type:
            raise ValueError(
                "Les types des champs doivent être identiques. "
                f"Source={source_type}, cible={target_type}.",
            )

        if source_type in {
            "SINGLE_CHOICE",
            "MULTIPLE_CHOICE",
        }:
            raise ValueError(
                "Les champs de type choix ne peuvent pas être utilisés " "comme clé de relation.",
            )

        existing = await self.session.execute(
            select(PluginResourceRelation).where(
                PluginResourceRelation.source_resource_id == source_resource.id,
                PluginResourceRelation.source_field_key == source_field.key,
                PluginResourceRelation.target_resource_id == target_resource.id,
                PluginResourceRelation.target_field_key == target_field.key,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError(
                "Cette relation existe déjà.",
            )

        # ------------------------------------------------------------------
        # Vérifier l'unicité des valeurs de la ressource cible.
        # ------------------------------------------------------------------

        target_records = await self._get_all_records(
            resource_id=target_resource.id,
        )

        seen_values: set[str] = set()

        for record in target_records:

            value = (record.data or {}).get(
                target_field.key,
            )

            if self._is_empty(value):
                continue

            normalized = self._relation_value_key(
                value,
            )

            if normalized in seen_values:
                raise ValueError(
                    "Impossible de créer la relation : "
                    f"le champ cible « {target_field.label} » "
                    "contient déjà des valeurs dupliquées.",
                )

            seen_values.add(normalized)

        # ------------------------------------------------------------------
        # Création
        # ------------------------------------------------------------------

        relation = PluginResourceRelation(
            source_resource_id=source_resource.id,
            source_field_key=source_field.key,
            target_resource_id=target_resource.id,
            target_field_key=target_field.key,
            label=data.label,
            is_active=data.is_active,
        )

        self.session.add(relation)

        await self.session.flush()

        # ------------------------------------------------------------------
        # IMPORTANT :
        # Recharger explicitement la relation avec ses ressources.
        #
        # Les relations SQLAlchemy utilisent lazy="raise".
        # ------------------------------------------------------------------

        result = await self.session.execute(
            select(PluginResourceRelation)
            .options(
                selectinload(
                    PluginResourceRelation.source_resource,
                ),
                selectinload(
                    PluginResourceRelation.target_resource,
                ),
            )
            .where(
                PluginResourceRelation.id == relation.id,
            )
        )

        relation = result.scalar_one()

        return relation

    async def delete_relation(
        self,
        *,
        resource_id: int,
        relation_id: int,
    ) -> None:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        plugin = await self._get_plugin(
            plugin_id=resource.plugin_id,
        )

        self._ensure_plugin_editable(
            plugin,
        )

        result = await self.session.execute(
            select(PluginResourceRelation).where(
                PluginResourceRelation.id == relation_id,
                or_(
                    PluginResourceRelation.source_resource_id == resource_id,
                    PluginResourceRelation.target_resource_id == resource_id,
                ),
            )
        )

        relation = result.scalar_one_or_none()

        if relation is None:
            raise ValueError(
                "Relation introuvable.",
            )

        await self.session.delete(
            relation,
        )

        await self.session.flush()

    async def list_related_records(
        self,
        *,
        resource_id: int,
        record_id: int,
        relation_id: int,
        user_id: int,
        is_admin: bool,
    ) -> tuple[
        PluginResourceRelation,
        str,
        list[PluginResourceRecord],
    ]:

        source_resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        relation_result = await self.session.execute(
            select(PluginResourceRelation).where(
                PluginResourceRelation.id == relation_id,
                or_(
                    PluginResourceRelation.source_resource_id == resource_id,
                    PluginResourceRelation.target_resource_id == resource_id,
                ),
                PluginResourceRelation.is_active.is_(True),
            )
        )

        relation = relation_result.scalar_one_or_none()

        if relation is None:
            raise ValueError(
                "Relation introuvable.",
            )

        record_result = await self.session.execute(
            select(PluginResourceRecord).where(
                PluginResourceRecord.id == record_id,
                PluginResourceRecord.resource_id == resource_id,
            )
        )

        record = record_result.scalar_one_or_none()

        if record is None:
            raise ValueError(
                "Donnée introuvable.",
            )

        if not is_admin and record.user_id not in {
            None,
            user_id,
        }:
            raise ValueError(
                "Vous ne pouvez pas accéder à cette donnée.",
            )

        record_data = record.data or {}

        # ------------------------------------------------------------------------
        # SOURCE -> TARGET
        # ------------------------------------------------------------------------

        if relation.source_resource_id == resource_id:

            direction = "SOURCE_TO_TARGET"

            value = record_data.get(
                relation.source_field_key,
            )

            if self._is_empty(value):
                return relation, direction, []

            target_resource = await self._get_resource_or_fail(
                resource_id=relation.target_resource_id,
            )

            records = await self._get_visible_records_for_relation(
                resource=target_resource,
                user_id=user_id,
                is_admin=is_admin,
            )

            related = [
                target_record
                for target_record in records
                if self._relation_values_equal(
                    target_record.data.get(
                        relation.target_field_key,
                    ),
                    value,
                )
            ]

            return relation, direction, related

        # ------------------------------------------------------------------------
        # TARGET -> SOURCE
        # ------------------------------------------------------------------------

        direction = "TARGET_TO_SOURCE"

        value = record_data.get(
            relation.target_field_key,
        )

        if self._is_empty(value):
            return relation, direction, []

        target_source_resource = await self._get_resource_or_fail(
            resource_id=relation.source_resource_id,
        )

        records = await self._get_visible_records_for_relation(
            resource=target_source_resource,
            user_id=user_id,
            is_admin=is_admin,
        )

        related = [
            source_record
            for source_record in records
            if self._relation_values_equal(
                source_record.data.get(
                    relation.source_field_key,
                ),
                value,
            )
        ]

        return relation, direction, related

    async def _get_visible_records_for_relation(
        self,
        *,
        resource: PluginResource,
        user_id: int,
        is_admin: bool,
    ) -> list[PluginResourceRecord]:

        query = select(
            PluginResourceRecord,
        ).where(
            PluginResourceRecord.resource_id == resource.id,
        )

        if resource.scope == PluginResourceScope.GLOBAL:

            query = query.where(
                PluginResourceRecord.user_id.is_(None),
            )

        elif not is_admin:

            query = query.where(
                or_(
                    PluginResourceRecord.user_id.is_(None),
                    PluginResourceRecord.user_id == user_id,
                )
            )

        result = await self.session.execute(
            query.order_by(
                PluginResourceRecord.created_at.desc(),
            )
        )

        return list(
            result.scalars().all(),
        )

    @staticmethod
    def _relation_value_key(
        value: Any,
    ) -> str:

        if isinstance(value, bool):
            return f"bool:{value}"

        if isinstance(value, (int, float)):
            return f"number:{value}"

        return f"string:{str(value).strip()}"

    @classmethod
    def _relation_values_equal(
        cls,
        left: Any,
        right: Any,
    ) -> bool:

        if cls._is_empty(left) or cls._is_empty(right):
            return False

        return cls._relation_value_key(left) == cls._relation_value_key(right)

    # ========================================================================
    # GENERAL
    # ========================================================================

    async def _sync_schema_definition(
        self,
        resource_id: int,
    ) -> None:

        resource = await self._get_resource_or_fail(
            resource_id=resource_id,
        )

        resource.schema_definition = self._resource_schema(
            resource,
        )

        await self.session.flush()

    async def _reload(
        self,
        resource_id: int,
    ) -> PluginResource:

        result = await self.session.execute(
            select(PluginResource)
            .options(
                selectinload(
                    PluginResource.fields,
                ),
            )
            .where(
                PluginResource.id == resource_id,
            )
        )

        return result.scalar_one()

    @staticmethod
    def _is_empty(
        value: Any,
    ) -> bool:

        return value is None or (
            isinstance(
                value,
                str,
            )
            and not value.strip()
        )

    @staticmethod
    def _ensure_plugin_editable(
        plugin: Plugin,
    ) -> None:

        if plugin.status != PluginStatus.DRAFT:
            raise ValueError(
                "La configuration d'un plugin est possible " "uniquement lorsqu'il est en DRAFT.",
            )
