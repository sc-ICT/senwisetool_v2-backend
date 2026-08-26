from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_builder.enums import ProjectStatus
from app.models.form_builder.project_definition import (
    ProjectDefinition,
)
from app.schemas.form_builder.project_definition import (
    ProjectDefinitionCreate,
    ProjectDefinitionUpdate,
)


class ProjectDefinitionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        data: ProjectDefinitionCreate,
    ) -> ProjectDefinition:
        code = data.code.strip().upper()
        name = data.name.strip()
        project_type = data.project_type.strip()

        if not code:
            raise ValueError("Le code du projet est obligatoire.")

        if not name:
            raise ValueError("Le nom du projet est obligatoire.")

        if not project_type:
            raise ValueError("Le type du projet est obligatoire.")

        existing = await self.session.execute(
            select(ProjectDefinition).where(
                ProjectDefinition.code == code,
                ProjectDefinition.created_by == user_id,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError("Un projet avec ce code existe déjà.")

        project = ProjectDefinition(
            code=code,
            name=name,
            description=(
                data.description.strip() if data.description and data.description.strip() else None
            ),
            project_type=project_type,
            status=ProjectStatus.DRAFT,
            global_config=data.global_config,
            created_by=user_id,
        )

        self.session.add(project)

        await self.session.flush()

        return project

    async def list(
        self,
        *,
        user_id: int,
        include_archived: bool = False,
    ) -> list[ProjectDefinition]:
        statement = (
            select(ProjectDefinition)
            .where(
                ProjectDefinition.created_by == user_id,
            )
            .order_by(
                ProjectDefinition.name.asc(),
            )
        )

        if not include_archived:
            statement = statement.where(
                ProjectDefinition.status != ProjectStatus.ARCHIVED,
            )

        result = await self.session.execute(
            statement,
        )

        return list(result.scalars().all())

    async def get(
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

    async def update(
        self,
        *,
        project_id: int,
        user_id: int,
        data: ProjectDefinitionUpdate,
    ) -> ProjectDefinition:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        if data.name is not None:
            name = data.name.strip()

            if not name:
                raise ValueError("Le nom du projet est obligatoire.")

            project.name = name

        if data.description is not None:
            project.description = data.description.strip() or None

        if data.project_type is not None:
            project_type = data.project_type.strip()

            if not project_type:
                raise ValueError("Le type du projet est obligatoire.")

            project.project_type = project_type

        if data.global_config is not None:
            project.global_config = data.global_config

        if data.status is not None:
            project.status = data.status

        await self.session.flush()

        return project

    async def archive(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> ProjectDefinition:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        project.status = ProjectStatus.ARCHIVED

        await self.session.flush()

        return project
