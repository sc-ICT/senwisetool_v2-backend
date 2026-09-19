from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin_form_template import PluginFormTemplate
from app.models.plugin_project_template import (
    PluginProjectTemplate,
)
from app.schemas.plugin_form_template import (
    PluginFormTemplateCreate,
    PluginFormTemplateUpdate,
)


class PluginFormTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ============================================================
    # INTERNAL
    # ============================================================

    async def _get_project_template(
        self,
        plugin_id: int,
        project_template_id: int,
    ) -> PluginProjectTemplate | None:
        result = await self.session.execute(
            select(PluginProjectTemplate).where(
                PluginProjectTemplate.id == project_template_id,
                PluginProjectTemplate.plugin_id == plugin_id,
            )
        )

        return result.scalar_one_or_none()

    async def _get_form_template(
        self,
        project_template_id: int,
        template_id: int,
    ) -> PluginFormTemplate | None:
        result = await self.session.execute(
            select(PluginFormTemplate).where(
                PluginFormTemplate.id == template_id,
                PluginFormTemplate.project_template_id == project_template_id,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # LIST
    # ============================================================

    async def list(
        self,
        plugin_id: int,
        project_template_id: int,
        include_inactive: bool = False,
    ) -> list[PluginFormTemplate]:
        project_template = await self._get_project_template(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
        )

        if project_template is None:
            raise ValueError("Modèle de projet introuvable.")

        statement = select(PluginFormTemplate).where(
            PluginFormTemplate.project_template_id == project_template_id,
        )

        if not include_inactive:
            statement = statement.where(PluginFormTemplate.is_active.is_(True))

        statement = statement.order_by(
            PluginFormTemplate.position.asc(),
            PluginFormTemplate.id.asc(),
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    # ============================================================
    # GET
    # ============================================================

    async def get(
        self,
        plugin_id: int,
        project_template_id: int,
        template_id: int,
    ) -> PluginFormTemplate | None:
        project_template = await self._get_project_template(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
        )

        if project_template is None:
            raise ValueError("Modèle de projet introuvable.")

        return await self._get_form_template(
            project_template_id=project_template_id,
            template_id=template_id,
        )

    # ============================================================
    # CREATE
    # ============================================================

    async def create(
        self,
        plugin_id: int,
        project_template_id: int,
        user_id: int,
        data: PluginFormTemplateCreate,
    ) -> PluginFormTemplate:
        project_template = await self._get_project_template(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
        )

        if project_template is None:
            raise ValueError("Modèle de projet introuvable.")

        existing = await self.session.execute(
            select(PluginFormTemplate).where(
                PluginFormTemplate.project_template_id == project_template_id,
                PluginFormTemplate.key == data.key,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError(
                "Un modèle de formulaire avec cette clé " "existe déjà dans ce modèle de projet."
            )

        if data.max_instances is not None and data.max_instances < data.min_instances:
            raise ValueError("max_instances ne peut pas être inférieur " "à min_instances.")

        template = PluginFormTemplate(
            project_template_id=project_template_id,
            key=data.key,
            name=data.name,
            description=data.description,
            form_type=data.form_type,
            position=data.position,
            required=data.required,
            min_instances=data.min_instances,
            max_instances=data.max_instances,
            allow_user_use=data.allow_user_use,
            allow_user_customization=data.allow_user_customization,
            global_config=data.global_config,
            definition=data.definition,
            resource_bindings=data.resource_bindings,
            rules=data.rules,
            metrics=data.metrics,
        )

        self.session.add(template)

        await self.session.flush()

        await self.session.refresh(template)

        return template

    # ============================================================
    # UPDATE
    # ============================================================

    async def update(
        self,
        plugin_id: int,
        project_template_id: int,
        template_id: int,
        user_id: int,
        data: PluginFormTemplateUpdate,
    ) -> PluginFormTemplate:
        template = await self.get(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            template_id=template_id,
        )

        if template is None:
            raise ValueError("Modèle de formulaire introuvable.")

        values = data.model_dump(exclude_unset=True)

        if "key" in values:
            existing = await self.session.execute(
                select(PluginFormTemplate).where(
                    PluginFormTemplate.project_template_id == project_template_id,
                    PluginFormTemplate.key == values["key"],
                    PluginFormTemplate.id != template_id,
                )
            )

            if existing.scalar_one_or_none() is not None:
                raise ValueError("Un autre modèle de formulaire utilise déjà cette clé.")

        min_instances = values.get(
            "min_instances",
            template.min_instances,
        )

        max_instances = values.get(
            "max_instances",
            template.max_instances,
        )

        if max_instances is not None and max_instances < min_instances:
            raise ValueError("max_instances ne peut pas être inférieur " "à min_instances.")

        for field, value in values.items():
            setattr(
                template,
                field,
                value,
            )

        await self.session.flush()

        await self.session.refresh(template)

        return template

    # ============================================================
    # DELETE
    # ============================================================

    async def delete(
        self,
        plugin_id: int,
        project_template_id: int,
        template_id: int,
    ) -> None:
        template = await self.get(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            template_id=template_id,
        )

        if template is None:
            raise ValueError("Modèle de formulaire introuvable.")

        await self.session.delete(template)

        await self.session.flush()
