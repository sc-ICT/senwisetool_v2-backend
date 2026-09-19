from __future__ import annotations

from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin, PluginResource
from app.models.plugin_program import PluginProgram
from app.models.user import User
from app.schemas.plugin_program import (
    PluginProgramCreate,
    PluginProgramUpdate,
    ProgramSchedule,
)


class PluginProgramService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    # ========================================================================
    # INTERNAL
    # ========================================================================

    async def _get_plugin(
        self,
        plugin_id: int,
    ) -> Plugin:
        result = await self.session.execute(
            select(Plugin).where(
                Plugin.id == plugin_id,
            )
        )

        plugin = result.scalar_one_or_none()

        if plugin is None:
            raise ValueError("Plugin introuvable.")

        return plugin

    async def _get_program(
        self,
        plugin_id: int,
        program_id: int,
    ) -> PluginProgram | None:
        result = await self.session.execute(
            select(PluginProgram).where(
                PluginProgram.id == program_id,
                PluginProgram.plugin_id == plugin_id,
            )
        )

        return result.scalar_one_or_none()

    async def _validate_creator(
        self,
        creator: User,
    ) -> int:
        if creator.id is None:
            raise ValueError("Impossible d'identifier l'administrateur créateur.")

        result = await self.session.execute(
            select(User.id).where(
                User.id == creator.id,
            )
        )

        user_id = result.scalar_one_or_none()

        if user_id is None:
            raise ValueError("L'administrateur créateur est introuvable.")

        return user_id

    async def _validate_resources(
        self,
        plugin_id: int,
        bindings: list[dict],
    ) -> None:
        if not bindings:
            return

        resource_ids: set[int] = set()

        for item in bindings:
            if not isinstance(item, dict):
                raise ValueError("Une liaison de ressource est invalide.")

            resource_id = item.get("resource_id")

            if not isinstance(resource_id, int) or resource_id <= 0:
                raise ValueError(
                    "Le resource_id d'une liaison de ressource " "doit être un entier positif."
                )

            resource_ids.add(resource_id)

        result = await self.session.execute(
            select(PluginResource.id).where(
                PluginResource.plugin_id == plugin_id,
                PluginResource.id.in_(resource_ids),
            )
        )

        found = set(result.scalars().all())

        if found != resource_ids:
            raise ValueError("Une ou plusieurs ressources n'appartiennent " "pas à ce plugin.")

    @staticmethod
    def _normalize_key(value: str) -> str:
        return value.strip()

    @staticmethod
    def _normalize_optional_string(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    # ========================================================================
    # LIST
    # ========================================================================

    async def list(
        self,
        *,
        plugin_id: int,
        include_inactive: bool = False,
    ) -> list[PluginProgram]:
        await self._get_plugin(plugin_id)

        statement = (
            select(PluginProgram)
            .where(
                PluginProgram.plugin_id == plugin_id,
            )
            .order_by(
                PluginProgram.position.asc(),
                PluginProgram.id.asc(),
            )
        )

        if not include_inactive:
            statement = statement.where(
                PluginProgram.is_active.is_(True),
            )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    # ========================================================================
    # GET
    # ========================================================================

    async def get(
        self,
        *,
        plugin_id: int,
        program_id: int,
    ) -> PluginProgram | None:
        await self._get_plugin(plugin_id)

        return await self._get_program(
            plugin_id=plugin_id,
            program_id=program_id,
        )

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create(
        self,
        *,
        plugin_id: int,
        creator: User,
        data: PluginProgramCreate,
    ) -> PluginProgram:
        await self._get_plugin(plugin_id)

        created_by = await self._validate_creator(creator)

        key = self._normalize_key(data.key)
        name = self._normalize_key(data.name)

        if not key:
            raise ValueError("La clé du programme est obligatoire.")

        if not name:
            raise ValueError("Le nom du programme est obligatoire.")

        await self._validate_resources(
            plugin_id,
            data.resource_bindings,
        )

        existing_result = await self.session.execute(
            select(PluginProgram.id).where(
                PluginProgram.plugin_id == plugin_id,
                PluginProgram.key == key,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise ValueError("Un programme avec cette clé existe déjà dans ce plugin.")

        scope = data.scope

        owner_user_id = None

        if scope == "USER":
            owner_user_id = created_by

        schedule = ProgramSchedule.model_validate(
            data.schedule,
        )

        item = PluginProgram(
            plugin_id=plugin_id,
            key=key,
            code=self._normalize_optional_string(data.code),
            name=name,
            description=self._normalize_optional_string(
                data.description,
            ),
            icon=self._normalize_optional_string(data.icon),
            color=self._normalize_optional_string(data.color),
            position=data.position,
            status="DRAFT",
            is_active=True,
            scope=scope,
            created_by=created_by,
            owner_user_id=owner_user_id,
            allow_user_use=data.allow_user_use,
            allow_user_customization=data.allow_user_customization,
            allow_multiple_projects=data.allow_multiple_projects,
            allow_project_creation=data.allow_project_creation,
            configuration=deepcopy(data.configuration),
            project_rules=deepcopy(data.project_rules),
            resource_bindings=deepcopy(data.resource_bindings),
            schedule=schedule.model_dump(mode="json"),
        )

        self.session.add(item)

        await self.session.flush()

        await self.session.refresh(item)

        return item

    # ========================================================================
    # UPDATE
    # ========================================================================

    async def update(
        self,
        *,
        plugin_id: int,
        program_id: int,
        data: PluginProgramUpdate,
    ) -> PluginProgram:
        item = await self._get_program(
            plugin_id=plugin_id,
            program_id=program_id,
        )

        if item is None:
            raise ValueError("Programme introuvable.")

        payload = data.model_dump(
            exclude_unset=True,
        )

        if "key" in payload:
            key = payload["key"]

            if not isinstance(key, str):
                raise ValueError("La clé du programme est invalide.")

            key = key.strip()

            if not key:
                raise ValueError("La clé du programme est obligatoire.")

            duplicate_result = await self.session.execute(
                select(PluginProgram.id).where(
                    PluginProgram.plugin_id == plugin_id,
                    PluginProgram.key == key,
                    PluginProgram.id != program_id,
                )
            )

            if duplicate_result.scalar_one_or_none() is not None:
                raise ValueError("Un autre programme utilise déjà cette clé.")

            payload["key"] = key

        if "name" in payload:
            name = payload["name"]

            if not isinstance(name, str):
                raise ValueError("Le nom du programme est invalide.")

            name = name.strip()

            if not name:
                raise ValueError("Le nom du programme est obligatoire.")

            payload["name"] = name

        for field in (
            "code",
            "description",
            "icon",
            "color",
        ):
            if field in payload:
                value = payload[field]

                if value is not None:
                    if not isinstance(value, str):
                        raise ValueError(f"Le champ {field} est invalide.")

                    payload[field] = value.strip() or None

        if "scope" in payload:
            scope = payload["scope"]

            if scope not in {
                "GLOBAL",
                "USER",
            }:
                raise ValueError("La portée du programme est invalide.")

            if scope == "GLOBAL":
                payload["owner_user_id"] = None
            else:
                if item.owner_user_id is None:
                    payload["owner_user_id"] = item.created_by

        if "resource_bindings" in payload:
            await self._validate_resources(
                plugin_id,
                payload["resource_bindings"] or [],
            )

        if "schedule" in payload:
            schedule = ProgramSchedule.model_validate(
                payload["schedule"],
            )

            payload["schedule"] = schedule.model_dump(
                mode="json",
            )

        for field, value in payload.items():
            if field == "owner_user_id":
                setattr(item, field, value)
                continue

            setattr(
                item,
                field,
                deepcopy(value),
            )

        await self.session.flush()

        await self.session.refresh(item)

        return item

    # ========================================================================
    # DELETE
    # ========================================================================

    async def delete(
        self,
        *,
        plugin_id: int,
        program_id: int,
    ) -> None:
        item = await self._get_program(
            plugin_id=plugin_id,
            program_id=program_id,
        )

        if item is None:
            raise ValueError("Programme introuvable.")

        await self.session.delete(item)

        await self.session.flush()
