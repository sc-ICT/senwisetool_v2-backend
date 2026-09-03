from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.enums import FileNodeType
from app.models.file_node import FileNode
from app.models.form_builder.project import Project
from app.models.project_agent_assignment import (
    ProjectAgentAssignment,
    ProjectAgentAssignmentZone,
)
from app.services.file_system import (
    FileAlreadyExistsError,
    FileSystemService,
)


class ProjectAgentAssignmentService:

    ZONES_FOLDER_NAME = "zones"

    # Formats de fichiers actuellement acceptés pour les zones.
    # Cette liste pourra être modifiée plus tard sans changer
    # la logique d'affectation.
    ZONE_FILE_EXTENSIONS = {
        "kml",
        "geojson",
    }

    def __init__(
        self,
        session: AsyncSession,
        file_system: FileSystemService,
    ) -> None:
        self.session = session
        self.file_system = file_system

    # ========================================================================
    # PROJECT
    # ========================================================================

    async def _get_project(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> Project:
        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.created_by == user_id,
            )
        )

        project = result.scalar_one_or_none()

        if project is None:
            raise ValueError("Projet introuvable.")

        if project.project_folder_id is None:
            raise ValueError(
                "Le dossier du projet est introuvable.",
            )

        return project

    # ========================================================================
    # AGENT
    # ========================================================================

    async def _get_agent(
        self,
        *,
        agent_id: int,
        user_id: int,
    ) -> Agent:
        result = await self.session.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.user_id == user_id,
            )
        )

        agent = result.scalar_one_or_none()

        if agent is None:
            raise ValueError("Agent introuvable.")

        return agent

    # ========================================================================
    # ASSIGNMENT
    # ========================================================================

    async def _get_assignment(
        self,
        *,
        assignment_id: int,
        project_id: int,
        user_id: int,
    ) -> ProjectAgentAssignment:
        result = await self.session.execute(
            select(ProjectAgentAssignment)
            .join(Project)
            .where(
                ProjectAgentAssignment.id == assignment_id,
                ProjectAgentAssignment.project_id == project_id,
                Project.created_by == user_id,
            )
            .options(
                selectinload(ProjectAgentAssignment.agent),
                selectinload(ProjectAgentAssignment.zones).selectinload(
                    ProjectAgentAssignmentZone.file_node
                ),
            )
        )

        assignment = result.scalar_one_or_none()

        if assignment is None:
            raise ValueError("Affectation introuvable.")

        return assignment

    # ========================================================================
    # ZONES FOLDER
    # ========================================================================

    async def _get_or_create_zones_folder(
        self,
        *,
        user_id: int,
        project: Project,
    ) -> FileNode:
        """
        Garantit l'existence du dossier :

            Projet/
                zones/
        """

        if project.project_folder_id is None:
            raise ValueError(
                "Le dossier du projet est introuvable.",
            )

        result = await self.session.execute(
            select(FileNode).where(
                FileNode.id == project.project_folder_id,
                FileNode.user_id == user_id,
                FileNode.type == FileNodeType.FOLDER,
            )
        )

        project_folder = result.scalar_one_or_none()

        if project_folder is None:
            raise ValueError(
                "Le dossier du projet est introuvable.",
            )

        result = await self.session.execute(
            select(FileNode).where(
                FileNode.user_id == user_id,
                FileNode.parent_id == project_folder.id,
                FileNode.type == FileNodeType.FOLDER,
                FileNode.name.ilike(self.ZONES_FOLDER_NAME),
            )
        )

        zones_folder = result.scalar_one_or_none()

        if zones_folder is not None:
            return zones_folder

        return await self.file_system.create_folder(
            user_id=user_id,
            name=self.ZONES_FOLDER_NAME,
            parent_id=project_folder.id,
        )

    # ========================================================================
    # VALIDATION FICHIER DE ZONE
    # ========================================================================

    @classmethod
    def _validate_zone_filename(
        cls,
        filename: str | None,
    ) -> tuple[str, str]:
        if not filename:
            raise ValueError(
                "Le nom du fichier de zone est obligatoire.",
            )

        extension = Path(filename).suffix.lower().lstrip(".")

        if extension not in cls.ZONE_FILE_EXTENSIONS:
            allowed_extensions = ", ".join(f".{ext}" for ext in sorted(cls.ZONE_FILE_EXTENSIONS))

            raise ValueError(
                f"Format de zone non autorisé. " f"Formats acceptés : {allowed_extensions}.",
            )

        return filename, extension

    # ========================================================================
    # VALIDATION ZONE EXISTANTE
    # ========================================================================

    async def _get_existing_zone_file(
        self,
        *,
        zone_file_id: int,
        zones_folder_id: int,
        user_id: int,
    ) -> FileNode:
        result = await self.session.execute(
            select(FileNode).where(
                FileNode.id == zone_file_id,
                FileNode.user_id == user_id,
                FileNode.parent_id == zones_folder_id,
            )
        )

        file_node = result.scalar_one_or_none()

        if file_node is None:
            raise ValueError(
                "Le fichier de zone demandé n'existe pas " "dans le dossier des zones du projet.",
            )

        if file_node.type != FileNodeType.FILE:
            raise ValueError("L'élément sélectionné n'est pas un fichier.")

        extension = Path(file_node.name).suffix.lower().lstrip(".")

        if extension not in self.ZONE_FILE_EXTENSIONS:
            allowed_extensions = ", ".join(f".{ext}" for ext in sorted(self.ZONE_FILE_EXTENSIONS))

            raise ValueError(
                f"Seuls les fichiers {allowed_extensions} " "peuvent être utilisés comme zones.",
            )

        return file_node

    # ========================================================================
    # CREATE ASSIGNMENT
    # ========================================================================

    async def create(
        self,
        *,
        user_id: int,
        project_id: int,
        agent_id: int,
        zone_file_ids: list[int] | None = None,
    ) -> ProjectAgentAssignment:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        await self._get_agent(
            agent_id=agent_id,
            user_id=user_id,
        )

        existing_result = await self.session.execute(
            select(ProjectAgentAssignment.id).where(
                ProjectAgentAssignment.project_id == project_id,
                ProjectAgentAssignment.agent_id == agent_id,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise ValueError(
                "Cet agent est déjà affecté à ce projet.",
            )

        assignment = ProjectAgentAssignment(
            project_id=project.id,
            agent_id=agent_id,
        )

        self.session.add(assignment)

        await self.session.flush()

        # Les zones sont optionnelles.
        if zone_file_ids:
            zones_folder = await self._get_or_create_zones_folder(
                user_id=user_id,
                project=project,
            )

            existing_file_ids: set[int] = set()

            for zone_file_id in zone_file_ids:
                if zone_file_id in existing_file_ids:
                    continue

                file_node = await self._get_existing_zone_file(
                    zone_file_id=zone_file_id,
                    zones_folder_id=zones_folder.id,
                    user_id=user_id,
                )

                assignment_zone = ProjectAgentAssignmentZone(
                    assignment_id=assignment.id,
                    file_node_id=file_node.id,
                )

                self.session.add(assignment_zone)
                existing_file_ids.add(zone_file_id)

            await self.session.flush()

        return await self._get_assignment(
            assignment_id=assignment.id,
            project_id=project.id,
            user_id=user_id,
        )

    # ========================================================================
    # LIST
    # ========================================================================

    async def list_by_project(
        self,
        *,
        user_id: int,
        project_id: int,
    ) -> list[ProjectAgentAssignment]:
        await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        result = await self.session.execute(
            select(ProjectAgentAssignment)
            .join(Project)
            .where(
                ProjectAgentAssignment.project_id == project_id,
                Project.created_by == user_id,
            )
            .options(
                selectinload(ProjectAgentAssignment.agent),
                selectinload(ProjectAgentAssignment.zones).selectinload(
                    ProjectAgentAssignmentZone.file_node
                ),
            )
            .order_by(
                ProjectAgentAssignment.created_at.desc(),
            )
        )

        return list(result.scalars().unique().all())

    # ========================================================================
    # ADD EXISTING ZONES
    # ========================================================================

    async def add_existing_zones(
        self,
        *,
        user_id: int,
        project_id: int,
        assignment_id: int,
        zone_file_ids: list[int],
    ) -> ProjectAgentAssignment:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        assignment = await self._get_assignment(
            assignment_id=assignment_id,
            project_id=project_id,
            user_id=user_id,
        )

        zones_folder = await self._get_or_create_zones_folder(
            user_id=user_id,
            project=project,
        )

        existing_file_ids = {zone.file_node_id for zone in assignment.zones}

        for zone_file_id in zone_file_ids:
            if zone_file_id in existing_file_ids:
                continue

            file_node = await self._get_existing_zone_file(
                zone_file_id=zone_file_id,
                zones_folder_id=zones_folder.id,
                user_id=user_id,
            )

            assignment.zones.append(
                ProjectAgentAssignmentZone(
                    file_node_id=file_node.id,
                )
            )

            existing_file_ids.add(zone_file_id)

        await self.session.flush()

        return await self._get_assignment(
            assignment_id=assignment.id,
            project_id=project_id,
            user_id=user_id,
        )

    # ========================================================================
    # UPLOAD ZONES
    # ========================================================================

    async def upload_zones(
        self,
        *,
        user_id: int,
        project_id: int,
        assignment_id: int,
        files: list[UploadFile],
    ) -> ProjectAgentAssignment:
        project = await self._get_project(
            project_id=project_id,
            user_id=user_id,
        )

        assignment = await self._get_assignment(
            assignment_id=assignment_id,
            project_id=project_id,
            user_id=user_id,
        )

        zones_folder = await self._get_or_create_zones_folder(
            user_id=user_id,
            project=project,
        )

        created_nodes: list[FileNode] = []

        try:
            for upload in files:
                filename, extension = self._validate_zone_filename(
                    upload.filename,
                )

                content_type = upload.content_type

                if not content_type:
                    if extension == "kml":
                        content_type = "application/vnd.google-earth.kml+xml"
                    elif extension == "geojson":
                        content_type = "application/geo+json"
                    else:
                        content_type = "application/octet-stream"

                node = await self.file_system.import_file(
                    user_id=user_id,
                    source=upload.file,
                    name=filename,
                    parent_id=zones_folder.id,
                    mime_type=content_type,
                    extension=extension,
                )

                created_nodes.append(node)

                self.session.add(
                    ProjectAgentAssignmentZone(
                        assignment_id=assignment.id,
                        file_node_id=node.id,
                    )
                )

            await self.session.flush()

        except FileAlreadyExistsError as exc:
            raise ValueError(
                "Un fichier portant le même nom existe déjà " "dans les zones du projet.",
            ) from exc

        except Exception:
            for node in created_nodes:
                if node.storage_key:
                    try:
                        await self.file_system.storage.delete(
                            storage_key=node.storage_key,
                        )
                    except Exception:
                        pass

            raise

        return await self._get_assignment(
            assignment_id=assignment.id,
            project_id=project_id,
            user_id=user_id,
        )

    # ========================================================================
    # REMOVE ZONE FROM ASSIGNMENT
    # ========================================================================

    async def remove_zone(
        self,
        *,
        user_id: int,
        project_id: int,
        assignment_id: int,
        zone_id: int,
    ) -> ProjectAgentAssignment:
        assignment = await self._get_assignment(
            assignment_id=assignment_id,
            project_id=project_id,
            user_id=user_id,
        )

        result = await self.session.execute(
            select(ProjectAgentAssignmentZone).where(
                ProjectAgentAssignmentZone.id == zone_id,
                ProjectAgentAssignmentZone.assignment_id == assignment.id,
            )
        )

        zone = result.scalar_one_or_none()

        if zone is None:
            raise ValueError("Zone introuvable dans cette affectation.")

        await self.session.delete(zone)

        await self.session.flush()

        return await self._get_assignment(
            assignment_id=assignment.id,
            project_id=project_id,
            user_id=user_id,
        )

    # ========================================================================
    # DELETE ASSIGNMENT
    # ========================================================================

    async def delete(
        self,
        *,
        user_id: int,
        project_id: int,
        assignment_id: int,
    ) -> None:
        assignment = await self._get_assignment(
            assignment_id=assignment_id,
            project_id=project_id,
            user_id=user_id,
        )

        await self.session.delete(assignment)

        await self.session.flush()
