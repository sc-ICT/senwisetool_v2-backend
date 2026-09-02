from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_builder.form_definition import (
    FormDefinition,
)
from app.models.form_builder.form_question import FormQuestion
from app.models.form_builder.form_section import (
    FormSection,
)
from app.schemas.form_builder.form_section import (
    FormSectionConfig,
    FormSectionCreate,
    FormSectionUpdate,
)


class FormSectionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def _get_form(
        self,
        *,
        form_id: int,
        user_id: int,
    ) -> FormDefinition | None:
        result = await self.session.execute(
            select(FormDefinition).where(
                FormDefinition.id == form_id,
                FormDefinition.created_by == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def _validate_repeat_config(
        self,
        *,
        form_id: int,
        user_id: int,
        config: FormSectionConfig,
    ):
        repeat = config.repeat

        if not repeat.enabled:
            return

        if repeat.count_source is None:
            raise ValueError(
                "La section répétable doit définir " "une question source pour le nombre."
            )

        result = await self.session.execute(
            select(FormQuestion).where(
                FormQuestion.id == repeat.count_source.question_id,
                FormQuestion.form_id == form_id,
            )
        )

        source_question = result.scalar_one_or_none()

        if source_question is None:
            raise ValueError(
                "La question source du nombre de répétitions " "n'existe pas dans ce formulaire."
            )

    async def create(
        self,
        *,
        form_id: int,
        user_id: int,
        data: FormSectionCreate,
    ) -> FormSection:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        name = data.name.strip()

        if not name:
            raise ValueError("Le nom de la section est obligatoire.")

        result = await self.session.execute(
            select(
                func.coalesce(
                    func.max(
                        FormSection.position,
                    ),
                    -1,
                )
            ).where(
                FormSection.form_id == form_id,
            )
        )

        max_position = result.scalar_one()

        await self._validate_repeat_config(
            form_id=form_id,
            user_id=user_id,
            config=data.config,
        )

        section = FormSection(
            form_id=form_id,
            name=name,
            description=(
                data.description.strip() if data.description and data.description.strip() else None
            ),
            position=max_position + 1,
            config=data.config.model_dump(
                exclude_none=True,
            ),
        )

        self.session.add(section)

        await self.session.flush()

        return section

    async def list(
        self,
        *,
        form_id: int,
        user_id: int,
    ) -> list[FormSection]:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        result = await self.session.execute(
            select(FormSection)
            .where(
                FormSection.form_id == form_id,
            )
            .order_by(
                FormSection.position.asc(),
            )
        )

        return list(result.scalars().all())

    async def update(
        self,
        *,
        form_id: int,
        section_id: int,
        user_id: int,
        data: FormSectionUpdate,
    ) -> FormSection:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        result = await self.session.execute(
            select(FormSection).where(
                FormSection.id == section_id,
                FormSection.form_id == form_id,
            )
        )

        section = result.scalar_one_or_none()

        if section is None:
            raise ValueError("Section introuvable.")

        if data.name is not None:
            name = data.name.strip()

            if not name:
                raise ValueError("Le nom de la section est obligatoire.")

            section.name = name

        if data.description is not None:
            section.description = data.description.strip() or None

        if data.config is not None:
            await self._validate_repeat_config(
                form_id=form_id,
                user_id=user_id,
                config=data.config,
            )

            section.config = data.config.model_dump(
                exclude_none=True,
            )

        await self.session.flush()

        return section

    async def delete(
        self,
        *,
        form_id: int,
        section_id: int,
        user_id: int,
    ) -> None:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        result = await self.session.execute(
            select(FormSection).where(
                FormSection.id == section_id,
                FormSection.form_id == form_id,
            )
        )

        section = result.scalar_one_or_none()

        if section is None:
            raise ValueError("Section introuvable.")

        await self.session.delete(section)
        await self.session.flush()

    async def reorder(
        self,
        *,
        form_id: int,
        user_id: int,
        ordered_section_ids: list[int],
    ) -> list[FormSection]:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        result = await self.session.execute(
            select(FormSection)
            .where(
                FormSection.form_id == form_id,
            )
            .order_by(
                FormSection.position.asc(),
            )
        )

        sections = list(result.scalars().all())

        existing_ids = {section.id for section in sections}

        requested_ids = set(ordered_section_ids)

        if existing_ids != requested_ids:
            raise ValueError(
                "La liste des sections à réordonner " "ne correspond pas aux sections du formulaire."
            )

        for position, section_id in enumerate(ordered_section_ids):
            section = next(section for section in sections if section.id == section_id)

            section.position = position

        await self.session.flush()

        return sorted(
            sections,
            key=lambda section: section.position,
        )
