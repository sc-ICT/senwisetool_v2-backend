from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_builder.project_definition import (
    ProjectDefinition,
)
from app.models.form_builder.project_section import (
    ProjectSection,
)
from app.schemas.form_builder.project_section import (
    ProjectSectionCreate,
    ProjectSectionUpdate,
)


class ProjectSectionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def _get_project(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> ProjectDefinition | None:
        result = await self.session.execute(
            select(ProjectDefinition).where(
                ProjectDefinition.id == project_id,
                ProjectDefinition.created_by == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: int,
        user_id: int,
        data: ProjectSectionCreate,
    ) -> ProjectSection:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        name = data.name.strip()

        if not name:
            raise ValueError("Le nom de la section est obligatoire.")

        result = await self.session.execute(
            select(
                func.coalesce(
                    func.max(
                        ProjectSection.position,
                    ),
                    -1,
                )
            ).where(
                ProjectSection.project_id == project_id,
            )
        )

        max_position = result.scalar_one()

        section = ProjectSection(
            project_id=project_id,
            name=name,
            description=(
                data.description.strip() if data.description and data.description.strip() else None
            ),
            position=max_position + 1,
            config=data.config,
        )

        self.session.add(section)

        await self.session.flush()

        return section

    async def list(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> list[ProjectSection]:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        result = await self.session.execute(
            select(ProjectSection)
            .where(
                ProjectSection.project_id == project_id,
            )
            .order_by(
                ProjectSection.position.asc(),
            )
        )

        return list(result.scalars().all())

    async def update(
        self,
        *,
        project_id: int,
        section_id: int,
        user_id: int,
        data: ProjectSectionUpdate,
    ) -> ProjectSection:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        result = await self.session.execute(
            select(ProjectSection).where(
                ProjectSection.id == section_id,
                ProjectSection.project_id == project_id,
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
            section.config = data.config

        await self.session.flush()

        return section

    async def delete(
        self,
        *,
        project_id: int,
        section_id: int,
        user_id: int,
    ) -> None:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        result = await self.session.execute(
            select(ProjectSection).where(
                ProjectSection.id == section_id,
                ProjectSection.project_id == project_id,
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
        project_id: int,
        user_id: int,
        ordered_section_ids: list[int],
    ) -> list[ProjectSection]:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        result = await self.session.execute(
            select(ProjectSection)
            .where(
                ProjectSection.project_id == project_id,
            )
            .order_by(
                ProjectSection.position.asc(),
            )
        )

        sections = list(result.scalars().all())

        existing_ids = {section.id for section in sections}

        requested_ids = set(ordered_section_ids)

        if existing_ids != requested_ids:
            raise ValueError(
                "La liste des sections à réordonner " "ne correspond pas aux sections du projet."
            )

        for position, section_id in enumerate(ordered_section_ids):
            section = next(section for section in sections if section.id == section_id)

            section.position = position

        await self.session.flush()

        return sorted(
            sections,
            key=lambda section: section.position,
        )
