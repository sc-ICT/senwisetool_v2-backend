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
from app.schemas.plugin_resource import (
    PluginResourceCreate,
    PluginResourceFieldCreate,
    PluginResourceFieldUpdate,
    PluginResourceRecordCreate,
    PluginResourceRecordUpdate,
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

        self._validate_field(
            data,
        )

        await self._ensure_field_key_available(
            resource_id=resource_id,
            key=data.key.strip(),
        )

        field = self._build_field(
            resource_id=resource_id,
            data=data,
        )

        self.session.add(
            field,
        )

        await self.session.flush()

        await self._sync_schema_definition(
            resource_id,
        )

        return await self._reload(
            resource_id,
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

        self._validate_partial_field(
            data,
        )

        if data.key is not None:
            new_key = data.key.strip()

            if new_key != field.key:
                await self._ensure_field_key_available(
                    resource_id=resource_id,
                    key=new_key,
                    exclude_field_id=field_id,
                )

            field.key = new_key

        if data.label is not None:
            field.label = data.label.strip()

        if data.description is not None:
            field.description = data.description

        if data.field_type is not None:
            field.field_type = data.field_type

        if data.required is not None:
            field.required = data.required

        if "min_length" in data.model_fields_set:
            field.min_length = data.min_length

        if "max_length" in data.model_fields_set:
            field.max_length = data.max_length

        if "min_value" in data.model_fields_set:
            field.min_value = data.min_value

        if "max_value" in data.model_fields_set:
            field.max_value = data.max_value

        if "pattern" in data.model_fields_set:
            field.pattern = data.pattern

        if data.options is not None:
            field.options = data.options

        if "default_value" in data.model_fields_set:
            field.default_value = data.default_value

        if data.position is not None:
            field.position = data.position

        if data.is_active is not None:
            field.is_active = data.is_active

        self._validate_model_field_values(
            field,
        )

        await self.session.flush()

        await self._sync_schema_definition(
            resource_id,
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

        await self.session.delete(
            field,
        )

        await self.session.flush()

        await self._sync_schema_definition(
            resource_id,
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

        if data.data is not None:
            record.data = self.validate_record(
                schema=schema,
                data=data.data,
            )

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
