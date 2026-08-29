from __future__ import annotations

from copy import deepcopy
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FileNodeType
from app.models.form_builder.enums import ProjectStatus
from app.models.form_builder.project_definition import (
    ProjectDefinition,
)
from app.schemas.form_builder.project_definition import (
    ProjectDefinitionCreate,
    ProjectDefinitionUpdate,
)
from app.services.file_system import FileNotFoundError as FileSystemNotFoundError
from app.services.file_system import (
    FileSystemService,
)
from app.services.form_builder.project_code import generate_project_code
from app.services.form_builder.project_defaults import (
    DEFAULT_PROJECT_GLOBAL_CONFIG,
    merge_project_global_config,
)


class ProjectDefinitionService:
    def __init__(
        self,
        session: AsyncSession,
        file_system: FileSystemService,
    ) -> None:
        self.session = session
        self.file_system = file_system

    async def create(
        self,
        *,
        user_id: int,
        data: ProjectDefinitionCreate,
    ) -> ProjectDefinition:
        name = data.name.strip()
        project_type = data.project_type.strip()

        if not name:
            raise ValueError("Le nom du projet est obligatoire.")

        if not project_type:
            raise ValueError("Le type du projet est obligatoire.")

        code = generate_project_code(user_id)

        project = ProjectDefinition(
            code=code,
            name=name,
            description=(
                data.description.strip() if data.description and data.description.strip() else None
            ),
            project_type=project_type,
            status=ProjectStatus.DRAFT,
            global_config=deepcopy(
                DEFAULT_PROJECT_GLOBAL_CONFIG,
            ),
            created_by=user_id,
        )

        self.session.add(project)

        await self.session.flush()

        await self.ensure_project_folder(
            project=project,
            user_id=user_id,
        )

        return project

    async def ensure_project_folder(
        self,
        *,
        project: ProjectDefinition,
        user_id: int,
    ):
        """
        Retourne le dossier associé au projet.

        Si project_folder_id existe et que le dossier existe encore,
        il est réutilisé.

        Si la référence existe mais que le dossier a été supprimé,
        un nouveau dossier est créé et la référence est mise à jour.
        """

        if project.project_folder_id is not None:
            try:
                folder = await self.file_system.get_node(
                    user_id=user_id,
                    node_id=project.project_folder_id,
                )

                if folder.type == FileNodeType.FOLDER:
                    return folder

            except FileSystemNotFoundError:
                pass

        folder = await self.file_system.create_folder(
            user_id=user_id,
            name=project.code,
        )

        project.project_folder_id = folder.id

        await self.session.flush()

        return folder

    async def _ensure_attachments_enabled(
        self,
        *,
        project: ProjectDefinition,
    ) -> None:
        config = project.global_config or {}

        attachments = config.get("attachments")

        if not isinstance(attachments, dict):
            raise ValueError("La configuration des fichiers attachés est invalide.")

        if attachments.get("enabled") is not True:
            raise PermissionError("Les fichiers attachés ne sont pas activés pour ce projet.")

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
            project.global_config = merge_project_global_config(
                project.global_config,
                data.global_config,
            )

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

    async def delete(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> None:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        # --------------------------------------------------------
        # 1. Supprimer le dossier du projet et tout son contenu
        # --------------------------------------------------------

        if project.project_folder_id is not None:
            try:
                await self.file_system.delete(
                    user_id=user_id,
                    node_id=project.project_folder_id,
                )
            except FileSystemNotFoundError:
                # Le dossier a déjà été supprimé.
                pass

        # --------------------------------------------------------
        # 2. Supprimer le projet et ses données associées
        # --------------------------------------------------------

        await self.session.delete(project)

        await self.session.flush()

    async def list_project_files(
        self,
        *,
        project_id: int,
        user_id: int,
    ):
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        await self._ensure_attachments_enabled(
            project=project,
        )

        folder = await self.ensure_project_folder(
            project=project,
            user_id=user_id,
        )

        return await self.file_system.list_children(
            user_id=user_id,
            parent_id=folder.id,
        )

    async def upload_project_file(
        self,
        *,
        project_id: int,
        user_id: int,
        name: str,
        source: BinaryIO,
        mime_type: str | None = None,
        extension: str | None = None,
    ):
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        await self._ensure_attachments_enabled(
            project=project,
        )

        folder = await self.ensure_project_folder(
            project=project,
            user_id=user_id,
        )

        return await self.file_system.create_file(
            user_id=user_id,
            name=name,
            source=source,
            parent_id=folder.id,
            mime_type=mime_type,
            extension=extension,
        )

    async def delete_project_file(
        self,
        *,
        project_id: int,
        file_id: int,
        user_id: int,
    ) -> None:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        await self._ensure_attachments_enabled(
            project=project,
        )

        folder = await self.ensure_project_folder(
            project=project,
            user_id=user_id,
        )

        file_node = await self.file_system.get_node(
            user_id=user_id,
            node_id=file_id,
        )

        if file_node.parent_id != folder.id:
            raise PermissionError("Ce fichier n'appartient pas à ce projet.")

        if file_node.type != FileNodeType.FILE:
            raise ValueError("L'élément indiqué n'est pas un fichier.")

        await self.file_system.delete(
            user_id=user_id,
            node_id=file_id,
        )
